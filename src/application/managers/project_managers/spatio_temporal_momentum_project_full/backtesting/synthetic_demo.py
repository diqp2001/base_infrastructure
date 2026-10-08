"""
Synthetic demo of the Spatio-Temporal Momentum dashboard (no IBKR, no SQL Server).

Runs the SAME STMTradingCycle the Misbuffet algorithm runs, on synthetic daily
closes for the configured universe stored in an in-memory SQLite database, so
the Flask progress page, the result window and the PDF can be exercised
quickly.  The model is shrunk (hidden size, epochs) for speed.  Results are
illustrative only.
"""

import tempfile
from types import SimpleNamespace
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.application.managers.project_managers.spatio_temporal_momentum_project_full.config import (
    build_stm_configuration,
    get_config,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_research_report import (
    build_report,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_trading_cycle import (
    STMTradingCycle,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_universe import (
    STMUniverseService,
)
from src.application.services.misbuffet.data.market_data_history_service import MarketDataHistoryService


def synthetic_universe_closes(tickers, start: str, n_days: int, seed: int = 7) -> pd.DataFrame:
    """Market factor + sector-like clusters + mild return persistence."""
    rng = np.random.default_rng(seed)
    n = len(tickers)
    market = rng.normal(0.0003, 0.009, n_days)
    clusters = rng.normal(0.0, 0.006, (n_days, max(1, n // 2)))
    rets = np.zeros((n_days, n))
    for t in range(n_days):
        shock = market[t] + clusters[t, np.arange(n) // 2] + rng.normal(0, 0.012, n)
        rets[t] = shock + (0.06 * rets[t - 1] if t else 0.0)
    dates = pd.bdate_range(start, periods=n_days)
    return pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=dates, columns=list(tickers))


def _seed_closes(session, closes: pd.DataFrame, ids) -> None:
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    factor = CompanyShareFactorModel(name="close", group="price", subgroup="ohlc", frequency="1d",
                                     data_type="numeric", source="ibkr", definition="close",
                                     factor_type="company_share_factor")
    session.add(factor)
    session.commit()
    rows = [{"factor_id": factor.id, "entity_id": ids[t], "entity_type": "CompanyShare",
             "date": d.to_pydatetime(), "value": repr(float(px))}
            for d, row in closes.iterrows() for t, px in row.items()]
    session.bulk_insert_mappings(FactorValueModel, rows)
    session.commit()


def run_synthetic_demo(progress, backtest_sessions: int = 90, n_epochs: int = 15, seed: int = 7):
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.repository_factory import RepositoryFactory

    config = get_config()
    stm = build_stm_configuration(config)
    stm.model.params = {"hidden_dim": 8, "n_heads": 2, "prescale_dim": 4, "emb_dim": 4, "dropout": 0.1}
    stm.training.n_epochs = n_epochs
    stm.artifact_dir = tempfile.mkdtemp(prefix="stm_demo_")
    tickers = list(stm.universe.tickers)

    progress.phase("Preparing synthetic data (in-memory database)")
    history_rows = int(config["training_window"]) + 10
    closes = synthetic_universe_closes(tickers, config["price_history_start"], history_rows + backtest_sessions + 2, seed)
    engine = create_engine("sqlite:///:memory:")
    ModelBase.metadata.create_all(engine)
    session = Session(engine)
    factory = RepositoryFactory(session)
    ids = {t: 1000 + i for i, t in enumerate(tickers)}
    _seed_closes(session, closes, ids)
    universe_service = STMUniverseService(factory, stm.universe)
    universe = universe_service.ensure_universe(ids, closes.index[0].date())
    history = MarketDataHistoryService(SimpleNamespace(entity_service=SimpleNamespace(repository_factory=factory)))

    cycle = STMTradingCycle(factory, stm, history, ids, history_start=closes.index[0],
                            retrain_every_days=config["retrain_every_days"],
                            universe_service=universe_service, universe_id=universe.id,
                            gross_cap=config.get("gross_exposure_cap"), log=progress.log)

    progress.phase("Trading cycle: train / score / trade bar by bar (synthetic)")
    bars = [d + pd.Timedelta(hours=16) for d in closes.index[history_rows:history_rows + backtest_sessions]]
    with progress._lock:
        progress._state["bars_total"] = len(bars)
    results = []
    for t in bars:
        r = cycle.step(t)
        results.append(r)
        progress.on_step(r)

    progress.phase("Building research report (tables, figures, SHAP)")
    report = build_report(results, closes, stm, factory=factory)
    if report is not None:
        report.notes.insert(0, "SYNTHETIC DEMO DATA — illustrative only, not market data.")
    session.close()
    engine.dispose()
    return report
