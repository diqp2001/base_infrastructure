"""
Synthetic demo of the 10-minute Spatio-Temporal Momentum project (no IBKR, no SQL Server).

Runs the SAME STMTradingCycle the Misbuffet algorithm runs, on synthetic 10-minute
closes (09:30-15:50 bar starts, business days) for the configured universe stored
in an in-memory SQLite database as a raw TRADES `close` factor of frequency '10m',
so the frontier applies the intraday availability rule (bar stamped 10:00 known
from 10:10).  The model is shrunk (hidden size, epochs) for speed.  Results are
illustrative only.
"""

import tempfile
from types import SimpleNamespace
from typing import List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.application.managers.project_managers.spatio_temporal_momentum_project_10m.config import (
    build_stm_configuration,
    get_config,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_research_report import (
    build_report,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import (
    bars_per_session,
    frequency,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_trading_cycle import (
    STMTradingCycle,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_universe import (
    STMUniverseService,
)
from src.application.services.misbuffet.data.market_data_history_service import MarketDataHistoryService


def intraday_bar_starts(start: str, n_bars: int, bar_minutes: int) -> pd.DatetimeIndex:
    """The first ``n_bars`` bar START stamps of the regular sessions (09:30 ..) from ``start``."""
    per_session = bars_per_session(bar_minutes)
    days = pd.bdate_range(start, periods=n_bars // per_session + 2)
    stamps = [d + pd.Timedelta(hours=9, minutes=30) + pd.Timedelta(minutes=bar_minutes * k)
              for d in days for k in range(per_session)]
    return pd.DatetimeIndex(stamps[:n_bars])


def synthetic_universe_closes(tickers, start: str, n_bars: int, bar_minutes: int, seed: int = 7) -> pd.DataFrame:
    """Market factor + sector-like clusters + mild return persistence, per-bar volatility."""
    rng = np.random.default_rng(seed)
    n = len(tickers)
    scale = bars_per_session(bar_minutes) ** -0.5                    # daily vols spread over the session
    market = rng.normal(0.0, 0.009 * scale, n_bars)
    clusters = rng.normal(0.0, 0.006 * scale, (n_bars, max(1, n // 2)))
    rets = np.zeros((n_bars, n))
    for t in range(n_bars):
        shock = market[t] + clusters[t, np.arange(n) // 2] + rng.normal(0, 0.012 * scale, n)
        rets[t] = shock + (0.06 * rets[t - 1] if t else 0.0)
    index = intraday_bar_starts(start, n_bars, bar_minutes)
    return pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=index, columns=list(tickers))


def _seed_closes(session, closes: pd.DataFrame, ids, bar_minutes: int) -> None:
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    factor = CompanyShareFactorModel(name="close", group="price", subgroup="TRADES", frequency=frequency(bar_minutes),
                                     data_type="numeric", source="ibkr", definition="close",
                                     factor_type="company_share_factor")
    session.add(factor)
    session.commit()
    rows = [{"factor_id": factor.id, "entity_id": ids[t], "entity_type": "CompanyShare",
             "date": d.to_pydatetime(), "value": repr(float(px))}
            for d, row in closes.iterrows() for t, px in row.items()]
    session.bulk_insert_mappings(FactorValueModel, rows)
    session.commit()


def run_synthetic_demo(progress, backtest_bars: int = 78, n_epochs: int = 15, seed: int = 7,
                       tickers: Optional[List[str]] = None, return_results: bool = False):
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.repository_factory import RepositoryFactory

    config = get_config()
    stm = build_stm_configuration(config)
    stm.model.params = {"hidden_dim": 8, "n_heads": 2, "prescale_dim": 4, "emb_dim": 4, "dropout": 0.1}
    stm.training.n_epochs = n_epochs
    stm.artifact_dir = tempfile.mkdtemp(prefix="stm10m_demo_")
    if tickers is not None:
        stm.universe.tickers = list(tickers)
    tickers = list(stm.universe.tickers)
    bar_minutes = stm.bar_minutes

    progress.phase("Preparing synthetic 10-minute data (in-memory database)")
    history_rows = int(config["training_window"]) + bars_per_session(bar_minutes)
    closes = synthetic_universe_closes(tickers, config["price_history_start"], history_rows + backtest_bars + 2,
                                       bar_minutes, seed)
    engine = create_engine("sqlite:///:memory:")
    ModelBase.metadata.create_all(engine)
    session = Session(engine)
    factory = RepositoryFactory(session)
    ids = {t: 1000 + i for i, t in enumerate(tickers)}
    _seed_closes(session, closes, ids, bar_minutes)
    universe_service = STMUniverseService(factory, stm.universe)
    universe = universe_service.ensure_universe(ids, closes.index[0].date())
    history = MarketDataHistoryService(SimpleNamespace(entity_service=SimpleNamespace(repository_factory=factory)))

    cycle = STMTradingCycle(factory, stm, history, ids, history_start=closes.index[0].normalize(),
                            retrain_every_days=config["retrain_every_days"],
                            universe_service=universe_service, universe_id=universe.id,
                            gross_cap=config.get("gross_exposure_cap"), log=progress.log)

    progress.phase("Trading cycle: train / score / trade every 10 minutes (synthetic)")
    # a decision when a bar closes: bar start + bar length
    bars = [d + pd.Timedelta(minutes=bar_minutes) for d in closes.index[history_rows:history_rows + backtest_bars]]
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
    return (report, results) if return_results else report
