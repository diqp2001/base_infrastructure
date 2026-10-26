"""
Synthetic demo of the 10-minute cross-sectional momentum project (no IBKR, no SQL Server).

Runs the SAME CSMTradingCycle the Misbuffet algorithm runs, with this project's configuration (10-minute bars,
retrained every day), on synthetic 10-minute TRADES bars (close, volume, high, low) stored in an in-memory SQLite
database, with an implied-volatility series per share, a SPY share and an IRX index at the same bar size, then
builds the results report. The synthetic returns carry a little cross-sectional momentum (the previous bar's
relative winners keep a small edge) so the classifier has something to find. The Optuna study and the training
window are shrunk for speed. Results are illustrative only.
"""

import tempfile
from types import SimpleNamespace
from typing import List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.application.managers.project_managers.cross_sectionnal_project_10m.config import (
    BAR_MINUTES,
    BARS_PER_SESSION,
    build_csm_configuration,
    get_config,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_report import build_report
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_trading_cycle import (
    CSMTradingCycle,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import frequency
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_universe import (
    STMUniverseService,
)
from src.application.services.misbuffet.data.market_data_history_service import MarketDataHistoryService


def session_bars(start: str, n_sessions: int, bar_minutes: int = BAR_MINUTES) -> pd.DatetimeIndex:
    """Bar start times of ``n_sessions`` regular sessions (09:30 .. 15:50 for 10-minute bars)."""
    days = pd.bdate_range(start, periods=n_sessions)
    offsets = [pd.Timedelta(hours=9, minutes=30) + pd.Timedelta(minutes=bar_minutes * i)
               for i in range(int(390 / bar_minutes))]
    return pd.DatetimeIndex([d + o for d in days for o in offsets])


def synthetic_closes(tickers, index: pd.DatetimeIndex, seed: int = 11, persistence: float = 0.15) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = len(tickers)
    rets = np.zeros((len(index), n))
    for t in range(len(index)):
        market = rng.normal(0.00002, 0.0013)
        idio = rng.normal(0.0, 0.0025, n)
        prev = rets[t - 1] - rets[t - 1].mean() if t else 0.0
        rets[t] = market + idio + persistence * prev
    return pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=index, columns=list(tickers))


def synthetic_bars(closes: pd.DataFrame, seed: int = 11) -> dict:
    rng = np.random.default_rng(seed + 1)
    size = rng.lognormal(10.0, 0.6, closes.shape[1])
    volume = pd.DataFrame(size * rng.lognormal(0.0, 0.35, closes.shape), index=closes.index, columns=closes.columns)
    spread = np.abs(rng.normal(0.0, 0.0015, closes.shape))
    high = closes * (1.0 + spread + np.abs(rng.normal(0.0, 0.0008, closes.shape)))
    low = closes * (1.0 - spread - np.abs(rng.normal(0.0, 0.0008, closes.shape)))
    return {"close": closes, "volume": volume.round(), "high": high, "low": low}


def synthetic_implied_vols(closes: pd.DataFrame, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 4)
    level = rng.uniform(0.20, 0.35, closes.shape[1])
    noise = np.exp(np.cumsum(rng.normal(0.0, 0.004, closes.shape), axis=0))
    return pd.DataFrame(level * noise / noise.mean(axis=0), index=closes.index, columns=closes.columns)


def _seed(session, model, entity_type: str, factor_type: str, bars: dict, ids) -> None:
    """``bars`` = {series id: panel}: 'close', 'volume', ..., 'close|OPTION_IMPLIED_VOLATILITY' (10-minute rows)."""
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    for sid, panel in bars.items():
        field, _, subgroup = sid.partition("|")
        factor = model(name=field, group="price", subgroup=subgroup or "TRADES", frequency=frequency(BAR_MINUTES),
                       data_type="numeric", source="ibkr", definition=sid, factor_type=factor_type)
        session.add(factor)
        session.commit()
        rows = [{"factor_id": factor.id, "entity_id": ids[t], "entity_type": entity_type,
                 "date": d.to_pydatetime(), "value": repr(float(v))}
                for d, row in panel.iterrows() for t, v in row.items() if np.isfinite(v)]
        session.bulk_insert_mappings(FactorValueModel, rows)
        session.commit()


def run_synthetic_demo(progress, backtest_sessions: int = 2, n_trials: int = 6, training_sessions: int = 4,
                       tickers: Optional[List[str]] = None, seed: int = 11, keep_cycle: bool = False):
    """keep_cycle: also return the results and the cycle, and leave its in-memory database open."""
    from src.infrastructure.models import ModelBase
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel, IndexFactorModel
    from src.infrastructure.repositories.repository_factory import RepositoryFactory

    config = get_config()
    csm = build_csm_configuration(config)
    csm.optimization.n_trials = n_trials
    csm.optimization.n_startup_trials = min(4, n_trials)
    csm.optimization.timeout_seconds = None
    csm.training.training_window_rows = training_sessions * BARS_PER_SESSION
    csm.artifact_dir = tempfile.mkdtemp(prefix="csm10m_demo_")
    if tickers is not None:
        csm.universe.tickers = list(tickers)
    tickers = list(csm.universe.tickers)

    progress.phase("Preparing synthetic 10-minute data (in-memory database)")
    history_bars = csm.training.training_window_rows + csm.features.warmup_rows() + 2
    history_sessions = int(np.ceil(history_bars / BARS_PER_SESSION))
    index = session_bars("2026-09-01", history_sessions + backtest_sessions)
    closes = synthetic_closes(tickers, index, seed)
    engine = create_engine("sqlite:///:memory:")
    ModelBase.metadata.create_all(engine)
    session = Session(engine)
    factory = RepositoryFactory(session)
    ids = {t: 1000 + i for i, t in enumerate(tickers)}
    spy = pd.DataFrame({"SPY": closes.mean(axis=1)})
    bars = synthetic_bars(closes, seed)
    for field, panel in bars.items():
        bars[field] = panel.join(synthetic_bars(spy, seed + 3)[field])
    bars["close|OPTION_IMPLIED_VOLATILITY"] = synthetic_implied_vols(closes, seed)
    _seed(session, CompanyShareFactorModel, "CompanyShare", "company_share_factor", bars, {**ids, "SPY": 999})
    irx = pd.DataFrame({"IRX": 40.0 + np.cumsum(np.random.default_rng(seed + 5).normal(0.0, 0.01, len(index)))},
                       index=index)
    _seed(session, IndexFactorModel, "Index", "index_factor", {"close": irx}, {"IRX": 998})
    universe_service = STMUniverseService(factory, csm.universe)
    universe = universe_service.ensure_universe(ids, index[0].date())
    history = MarketDataHistoryService(SimpleNamespace(entity_service=SimpleNamespace(repository_factory=factory)))
    cycle = CSMTradingCycle(factory, csm, history, ids, history_start=index[0].normalize(),
                            retrain_every_days=config["retrain_every_days"], universe_service=universe_service,
                            universe_id=universe.id, log=progress.log, benchmark_entities={"SPY": 999, "IRX": 998})

    progress.phase("Trading cycle: Optuna TPE / train / score / trade every 10 minutes (synthetic)")
    # the engine clock: a bar stamped t is known from t + 10 minutes
    clock = [t + pd.Timedelta(minutes=BAR_MINUTES) for t in index[-backtest_sessions * BARS_PER_SESSION:]]
    with progress._lock:
        progress._state["bars_total"] = len(clock)
    results = []
    for t in clock:
        r = cycle.step(t)
        results.append(r)
        progress.on_step(r)

    progress.phase("Building results report")
    used = {r.artifact_id for r in results if r.artifact_id is not None}
    artifacts = {a.id: m for a, m in cycle.artifact_store.list_artifacts() if a.id in used}
    report = build_report(results, closes, csm, artifacts, history_start=index[0].normalize(),
                          feature_engine=cycle.feature_engine)
    if report is not None:
        report.notes.insert(0, "SYNTHETIC DEMO DATA — illustrative only, not market data.")
    if keep_cycle:
        return report, results, cycle
    session.close()
    engine.dispose()
    return report
