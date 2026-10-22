"""
STMTradingCycle — the time-driven Spatio-Temporal Momentum loop, called once
per bar by the Misbuffet algorithm (backtest) or the live engine.  There is
no separate research path: what runs in a backtest is what runs live.

step(now):
  1. advance the MarketDataHistoryService frontier to ``now``
  2. let the data updater import any new bars (IBKR via MarketDataService)
  3. read closes THROUGH THE FRONTIER — only bars closed at ``now``
  4. decision session = last session with a known close
  5. eligible assets = active universe constituents with enough history
     known at the session (never judged on their future history)
  6. retrain when due (every ``retrain_every_days``) or when the model's
     assets are no longer all eligible: train on data known at the session,
     validation = the latest ``val_days``; the new model is used from the
     NEXT session (artifact selection requires validation_end < session)
  7. score the universe with the current model, store the signals
  8. return vol-scaled target weights for set_holdings
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_artifact_store import (
    STMArtifactStore,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_backtest import (
    signals_to_weights,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMConfiguration,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import (
    align_close_panel,
    build_feature_panel,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_feature_store import (
    STMFeatureStore,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_model_provider import (
    SpatioTemporalMomentumModelProvider,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_price_history import (
    STMFrontierPriceReader,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_walk_forward import (
    STMWalkForwardTrainer,
)
from src.application.services.timing.step_timings import timed


@dataclass
class CycleResult:
    time: pd.Timestamp
    session: Optional[pd.Timestamp] = None
    eligible: List[str] = field(default_factory=list)
    retrained: bool = False
    artifact_id: Optional[int] = None
    scores: Dict[str, float] = field(default_factory=dict)       # ticker -> signal
    daily_vol: Dict[str, float] = field(default_factory=dict)    # ticker -> daily vol at session
    weights: Dict[str, float] = field(default_factory=dict)      # ticker -> target weight
    note: str = ""
    # False when the decision session did not change since the previous step (e.g. an
    # intraday engine clock): the previous decision is returned and must not be re-traded.
    new_decision: bool = True


class STMTradingCycle:

    def __init__(self, factory, config: STMConfiguration, history_service,
                 ticker_to_entity: Dict[str, int], history_start,
                 retrain_every_days: int = 365, data_updater: Optional[Callable] = None,
                 universe_service=None, universe_id: Optional[int] = None,
                 gross_cap: Optional[float] = 1.0, persist: bool = True,
                 log: Optional[Callable[[str], None]] = None):
        self.factory = factory
        self.config = config
        self.history_service = history_service
        self.ticker_to_entity = dict(ticker_to_entity)
        self.history_start = pd.Timestamp(history_start)
        self.retrain_every_days = int(retrain_every_days)
        self.data_updater = data_updater
        self.universe_service = universe_service
        self.universe_id = universe_id
        self.gross_cap = gross_cap
        self.persist = persist
        self.log = log or (lambda msg: None)

        from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import frequency
        self.reader = STMFrontierPriceReader(history_service, frequency=frequency(config.bar_minutes),
                                             bar_minutes=config.bar_minutes)
        self.trainer = STMWalkForwardTrainer(config, factory=factory, log=self.log)
        self.artifact_store = STMArtifactStore(factory, config)
        self.provider = SpatioTemporalMomentumModelProvider(
            factory=factory, config=config, price_reader=self.reader, artifact_store=self.artifact_store,
        )
        self.feature_store = STMFeatureStore(factory, config) if persist else None
        self._last_result: Optional[CycleResult] = None

    # ------------------------------------------------------------------

    def _eligible(self, closes: pd.DataFrame, session: pd.Timestamp) -> List[str]:
        required = self._required_rows()
        active = None
        if self.universe_service is not None:
            active_ids = set(self.universe_service.active_entity_ids(session.date()))
            active = {t for t, eid in self.ticker_to_entity.items() if eid in active_ids}
        eligible = []
        for ticker in self.ticker_to_entity:                       # configured order
            if active is not None and ticker not in active:
                continue
            col = closes.get(ticker)
            if col is None or pd.isna(col.get(session, np.nan)):
                continue                                             # no close today (e.g. delisted)
            if int(col.notna().sum()) >= required:
                eligible.append(ticker)
        return eligible

    def _required_rows(self) -> int:
        """Sessions of history an asset needs: the rolling training window, or the feature warm-up."""
        rows = self.config.training.rolling_window_rows
        return int(rows) if rows else self.config.features.required_history_days(self.config.model.lookback)

    def _newest_artifact_meta(self, session: pd.Timestamp) -> Optional[dict]:
        metas = [m for _, m in self.artifact_store.list_artifacts()
                 if m.get("validation_end") and pd.Timestamp(m["validation_end"]) <= session]
        return max(metas, key=lambda m: pd.Timestamp(m["validation_end"])) if metas else None

    def _retrain_due(self, session: pd.Timestamp, eligible: List[str]) -> bool:
        newest = self._newest_artifact_meta(session)
        if newest is None:
            return True
        last = pd.Timestamp(newest["validation_end"])
        if last == session:
            return False                                             # already trained this session
        if (session - last).days >= self.retrain_every_days:
            return True
        return not set(newest["assets"]).issubset(eligible)          # model assets left the universe

    def _train(self, closes: pd.DataFrame, session: pd.Timestamp, eligible: List[str]):
        # Training close panel: one column per eligible asset, one row per session.
        #   closes[eligible]  keep only assets that may be traded at this session
        #                     (active constituents with enough known history);
        #   .loc[:session]    no row after the decision session (the frontier
        #                     already guarantees it; this keeps the intent explicit);
        #   align_close_panel inner-joins the assets on dates: a date is kept only
        #                     if EVERY asset has a close that day, because the model
        #                     reads all assets jointly at each time step. Missing
        #                     dates are dropped and counted in `report`, never filled.
        with timed("features"):
            aligned, report = align_close_panel(closes[eligible].loc[:session])
            rows = self.config.training.rolling_window_rows
            if rows:
                aligned = aligned.iloc[-int(rows):]                   # rolling window known at the session
        if aligned.shape[1] < 2 or len(aligned) == 0:
            return None
        # Feature panel: turns the aligned closes into the model's inputs and labels.
        #   features   [dates, assets, features]  per asset, from closes up to each date only:
        #              vol-normalised returns over each horizon + normalised MACD signals
        #              (windows from config.features), after winsorising the prices;
        #   target     [dates, assets]  training label: return from the date to
        #              date + prediction_horizon, scaled to the volatility target
        #              (NaN for the last dates, whose future is not known yet);
        #   daily_vol  [dates, assets]  EWM volatility, used for the label and position sizing;
        #   first_valid_row  first date where every feature exists (earlier rows are warm-up).
        with timed("features"):
            panel = build_feature_panel(aligned, self.config.features, self.config.prediction_horizon)
        ids = {t: self.ticker_to_entity[t] for t in panel.assets}
        with timed("train"):
            return self.trainer.train_as_of(panel, session, ids, universe_id=self.universe_id,
                                            valid_days=self.retrain_every_days)

    # ------------------------------------------------------------------

    def step(self, now) -> CycleResult:
        now = pd.Timestamp(now)
        self.history_service.set_frontier(now.to_pydatetime())
        result = CycleResult(time=now)
        if self.data_updater is not None:
            with timed("update"):
                self.data_updater(now)

        id_to_ticker = {eid: t for t, eid in self.ticker_to_entity.items()}
        with timed("read"):
            closes = self.reader.load_close_panel(id_to_ticker, start=self.history_start)
        if closes.empty:
            result.note = "no closes known yet"
            return result
        session = closes.index.max()
        if self._last_result is not None and self._last_result.session == session:
            # Same decision session as the previous step (intraday clock): nothing new is
            # known, so reuse the decision instead of re-scoring, retraining or re-trading.
            return replace(self._last_result, time=now, retrained=False, artifact_id=None,
                           new_decision=False, note="same session as the previous decision")
        result.session = session
        self._last_result = result
        eligible = self._eligible(closes, session)
        result.eligible = eligible

        with timed("read"):
            retrain_due = self._retrain_due(session, eligible)
        if retrain_due:
            wr = self._train(closes, session, eligible)
            if wr is not None:
                result.retrained = True
                result.artifact_id = wr.artifact_id

        details = self.provider.score_details(session)
        if not details:
            result.note = result.note or "no model eligible for this session yet"
            return result

        result.scores = {d["ticker"]: d["score"] for d in details}
        result.daily_vol = {d["ticker"]: d["daily_vol"] for d in details}
        from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import periods_per_year
        result.weights = signals_to_weights(result.scores, result.daily_vol,
                                            self.config.training.target_vol, self.gross_cap,
                                            periods_per_year=periods_per_year(self.config.bar_minutes))
        if self.persist:
            with timed("persist"):
                self.feature_store.write_signals(session, {d["entity_id"]: d["score"] for d in details})
        return result
