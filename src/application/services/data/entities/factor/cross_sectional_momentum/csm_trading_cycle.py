"""
CSMTradingCycle — the time-driven cross-sectional momentum loop, called once per bar by the Misbuffet algorithm
(backtest) or the live engine; the same code runs in both.

step(now):
  1. advance the MarketDataHistoryService frontier to ``now``
  2. let the data updater import any new bars (IBKR via MarketDataService, writes only)
  3. read daily closes THROUGH THE FRONTIER — only bars closed at ``now``
  4. decision session = last session with a known close
  5. features = the 24 momentum factors (their own calculate() on the closes known at the session);
     eligible assets = active universe constituents with a close at the session and every feature of the model
  6. retrain when due (every ``retrain_every_days`` calendar days): Optuna TPE study (features + LightGBM
     hyper-parameters) on the rolling window of labels known at the session, then the final model
  7. score the eligible assets (probability of beating the cross-sectional median), store the signals
  8. long the top / short the bottom quantile, inverse-volatility weights, dollar-neutral, gross capped
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.cross_sectional_momentum.csm_artifact_store import (
    CSMArtifactStore,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
    CSMConfiguration,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import (
    CSMFeatureEngine,
    build_dataset,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_model import train
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_signal_store import CSMSignalStore
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_price_history import (
    STMFrontierPriceReader,
)


@dataclass
class CSMCycleResult:
    time: pd.Timestamp
    session: Optional[pd.Timestamp] = None
    eligible: List[str] = field(default_factory=list)
    retrained: bool = False
    artifact_id: Optional[int] = None              # model used for the scores
    scores: Dict[str, float] = field(default_factory=dict)        # ticker -> probability
    daily_vol: Dict[str, float] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)
    shap: Dict[str, float] = field(default_factory=dict)          # feature -> mean |TreeSHAP| over the scored assets
    features_used: List[str] = field(default_factory=list)
    note: str = ""
    new_decision: bool = True


def long_short_weights(scores: Dict[str, float], daily_vol: Dict[str, float], quantile: float,
                       gross: float) -> Dict[str, float]:
    """Long the top / short the bottom ``quantile`` of scores, inverse-vol inside each side, each side gross/2."""
    usable = {a: s for a, s in scores.items()
              if np.isfinite(s) and np.isfinite(daily_vol.get(a, np.nan)) and daily_vol.get(a, 0) > 0}
    n = len(usable)
    k = int(np.floor(n * quantile))
    if n < 2 or k < 1:
        return {}
    ranked = sorted(usable, key=lambda a: usable[a])
    shorts, longs = ranked[:k], ranked[-k:]
    weights: Dict[str, float] = {}
    for side, names in ((1.0, longs), (-1.0, shorts)):
        inv = {a: 1.0 / daily_vol[a] for a in names}
        total = sum(inv.values())
        for a, v in inv.items():
            weights[a] = side * (gross / 2.0) * v / total
    return weights


class CSMTradingCycle:

    def __init__(self, factory, config: CSMConfiguration, history_service, ticker_to_entity: Dict[str, int],
                 history_start, retrain_every_days: int = 21, data_updater: Optional[Callable] = None,
                 universe_service=None, universe_id: Optional[int] = None, persist: bool = True,
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
        self.persist = persist and config.persist_signals
        self.log = log or (lambda msg: None)
        self.reader = STMFrontierPriceReader(history_service, frequency="1d")
        self.artifact_store = CSMArtifactStore(factory, config)
        self.signal_store = CSMSignalStore(factory, config) if self.persist else None
        self.feature_engine = CSMFeatureEngine(config.features)      # domain factors' calculate(), cached
        self._last_result: Optional[CSMCycleResult] = None
        self._loaded: Dict[int, object] = {}

    # ------------------------------------------------------------------

    def _active(self, session: pd.Timestamp) -> List[str]:
        if self.universe_service is None:
            return list(self.ticker_to_entity)
        ids = set(self.universe_service.active_entity_ids(session.date()))
        return [t for t, eid in self.ticker_to_entity.items() if eid in ids]

    def _retrain_due(self, session: pd.Timestamp) -> bool:
        selected = self.artifact_store.select(session)
        if selected is None:
            return True
        last = pd.Timestamp(selected[1]["trained_as_of"])
        return last < session and (session - last).days >= self.retrain_every_days

    def _train(self, dataset, session: pd.Timestamp) -> Optional[int]:
        dates = sorted(set(dataset.frame.index.get_level_values("date")))
        labelled = sorted(set(dataset.frame.dropna(subset=["label"]).index.get_level_values("date")))
        window = [d for d in labelled if d <= session][-self.config.training.training_window_rows:]
        if len(window) < (self.config.optimization.n_folds + 1) * 5:
            self.log(f"[CSM] not enough labelled sessions to train at {session.date()} ({len(window)})")
            return None
        self.log(f"[CSM] train_as_of {session.date()}: {len(window)} sessions ({window[0].date()} .. "
                 f"{window[-1].date()}), {len(dates)} sessions known")
        model = train(dataset, window, self.config, log=self.log)
        artifact, _ = self.artifact_store.save(model, session, self.universe_id, list(self.ticker_to_entity))
        return int(artifact.id)

    def _model(self, session: pd.Timestamp):
        selected = self.artifact_store.select(session)
        if selected is None:
            return None
        artifact = selected[0]
        if artifact.id not in self._loaded:
            self._loaded[artifact.id] = self.artifact_store.load(artifact)
        return self._loaded[artifact.id]

    # ------------------------------------------------------------------

    def step(self, now) -> CSMCycleResult:
        now = pd.Timestamp(now)
        self.history_service.set_frontier(now.to_pydatetime())
        result = CSMCycleResult(time=now)
        if self.data_updater is not None:
            self.data_updater(now)

        id_to_ticker = {eid: t for t, eid in self.ticker_to_entity.items()}
        closes = self.reader.load_close_panel(id_to_ticker, start=self.history_start)
        if closes.empty:
            result.note = "no closes known yet"
            return result
        session = closes.index.max()
        if self._last_result is not None and self._last_result.session == session:
            return replace(self._last_result, time=now, retrained=False, new_decision=False,
                           note="same session as the previous decision")
        result.session = session
        self._last_result = result

        dataset = build_dataset(closes, self.config.features, self.config.label, self.feature_engine)
        if self._retrain_due(session):
            artifact_id = self._train(dataset, session)
            if artifact_id is not None:
                result.retrained = True

        model = self._model(session)
        if model is None:
            result.note = "no model trained yet"
            return result
        today = dataset.rows_on(session)
        active = set(self._active(session))
        today = today[today.index.isin(active)].dropna(subset=model.features + ["daily_vol"])
        result.eligible = [t for t in self.ticker_to_entity if t in today.index]
        if len(today) < 2:
            result.note = "fewer than two assets with every feature at the session"
            return result

        p = model.predict_proba(today)
        contrib = np.abs(model.contributions(today)).mean(axis=0)
        result.artifact_id = model.artifact_id
        result.features_used = list(model.features)
        result.scores = {a: float(v) for a, v in zip(today.index, p)}
        result.daily_vol = {a: float(v) for a, v in today["daily_vol"].items()}
        result.shap = {f: float(v) for f, v in zip(model.features, contrib)}
        result.weights = long_short_weights(result.scores, result.daily_vol,
                                            self.config.training.long_short_quantile,
                                            self.config.training.gross_exposure)
        if self.signal_store is not None:
            self.signal_store.write(session, {self.ticker_to_entity[a]: s for a, s in result.scores.items()})
        return result
