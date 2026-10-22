"""
Synthetic demo of the cross-sectional momentum project (no IBKR, no SQL Server).

Runs the SAME CSMTradingCycle the Misbuffet algorithm runs, on synthetic daily closes stored in an in-memory
SQLite database as a raw TRADES `close` factor, then builds the results report. The synthetic returns carry a
little cross-sectional momentum (yesterday's relative winners keep a small edge) so the classifier has something
to find. The Optuna study is shrunk for speed. Results are illustrative only.
"""

import tempfile
from types import SimpleNamespace
from typing import List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.application.managers.project_managers.cross_sectionnal_project.config import (
    build_csm_configuration,
    get_config,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_report import build_report
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_trading_cycle import (
    CSMTradingCycle,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_universe import (
    STMUniverseService,
)
from src.application.services.misbuffet.data.market_data_history_service import MarketDataHistoryService


def synthetic_closes(tickers, start: str, n_days: int, seed: int = 11, persistence: float = 0.15) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = len(tickers)
    rets = np.zeros((n_days, n))
    for t in range(n_days):
        market = rng.normal(0.0002, 0.008)
        idio = rng.normal(0.0, 0.015, n)
        prev = rets[t - 1] - rets[t - 1].mean() if t else 0.0
        rets[t] = market + idio + persistence * prev
    dates = pd.bdate_range(start, periods=n_days)
    return pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=dates, columns=list(tickers))


def _seed_closes(session, closes: pd.DataFrame, ids) -> None:
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    factor = CompanyShareFactorModel(name="close", group="price", subgroup="TRADES", frequency="1d",
                                     data_type="numeric", source="ibkr", definition="close",
                                     factor_type="company_share_factor")
    session.add(factor)
    session.commit()
    rows = [{"factor_id": factor.id, "entity_id": ids[t], "entity_type": "CompanyShare",
             "date": d.to_pydatetime(), "value": repr(float(px))}
            for d, row in closes.iterrows() for t, px in row.items() if np.isfinite(px)]
    session.bulk_insert_mappings(FactorValueModel, rows)
    session.commit()


def run_synthetic_demo(progress, backtest_sessions: int = 40, n_trials: int = 8, training_window: int = 120,
                       retrain_every_days: int = 14, tickers: Optional[List[str]] = None, seed: int = 11,
                       return_results: bool = False, keep_cycle: bool = False):
    """keep_cycle: also return the cycle and leave its in-memory database open (the caller disposes of it)."""
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.repository_factory import RepositoryFactory

    config = get_config()
    csm = build_csm_configuration(config)
    csm.optimization.n_trials = n_trials
    csm.optimization.n_startup_trials = min(4, n_trials)
    csm.optimization.timeout_seconds = None
    csm.training.training_window_rows = training_window
    csm.artifact_dir = tempfile.mkdtemp(prefix="csm_demo_")
    if tickers is not None:
        csm.universe.tickers = list(tickers)
    tickers = list(csm.universe.tickers)

    progress.phase("Preparing synthetic data (in-memory database)")
    history_rows = training_window + csm.features.warmup_rows() + 5
    closes = synthetic_closes(tickers, "2025-01-02", history_rows + backtest_sessions + 2, seed)
    engine = create_engine("sqlite:///:memory:")
    ModelBase.metadata.create_all(engine)
    session = Session(engine)
    factory = RepositoryFactory(session)
    ids = {t: 1000 + i for i, t in enumerate(tickers)}
    _seed_closes(session, closes, ids)
    universe_service = STMUniverseService(factory, csm.universe)
    universe = universe_service.ensure_universe(ids, closes.index[0].date())
    history = MarketDataHistoryService(SimpleNamespace(entity_service=SimpleNamespace(repository_factory=factory)))
    cycle = CSMTradingCycle(factory, csm, history, ids, history_start=closes.index[0],
                            retrain_every_days=retrain_every_days, universe_service=universe_service,
                            universe_id=universe.id, log=progress.log)

    progress.phase("Trading cycle: Optuna TPE / train / score / trade bar by bar (synthetic)")
    # the 16:00 bar of session D+1 sees the close of D (a daily bar is known from D+1 00:00)
    bars = [d + pd.Timedelta(hours=16) for d in closes.index[history_rows:history_rows + backtest_sessions]]
    with progress._lock:
        progress._state["bars_total"] = len(bars)
    results = []
    for t in bars:
        r = cycle.step(t)
        results.append(r)
        progress.on_step(r)

    progress.phase("Building results report")
    used = {r.artifact_id for r in results if r.artifact_id is not None}
    artifacts = {a.id: m for a, m in cycle.artifact_store.list_artifacts() if a.id in used}
    report = build_report(results, closes, csm, artifacts, history_start=closes.index[0],
                          feature_engine=cycle.feature_engine)
    if report is not None:
        report.notes.insert(0, "SYNTHETIC DEMO DATA — illustrative only, not market data.")
    if keep_cycle:
        return report, results, cycle
    session.close()
    engine.dispose()
    return (report, results) if return_results else report
