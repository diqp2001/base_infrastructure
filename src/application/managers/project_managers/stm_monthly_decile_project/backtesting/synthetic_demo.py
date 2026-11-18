"""
Synthetic demo of the monthly STM decile strategy (no IBKR, no SQL Server, no Eulerpool).

Runs the SAME STMDecileTradingCycle the Misbuffet algorithm runs, on synthetic daily closes of an equal-share index
of 20 members (one membership change), stored in an in-memory SQLite database as a raw TRADES `close` factor of
frequency '1d' and read through the MarketDataHistoryService frontier (a close dated D is known from D+1 00:00). The
STM model is shrunk for speed (monthly rows: short windows). Model B gets a synthetic point-in-time feature
(``extra_features``) standing in for the Eulerpool fundamentals. Results are illustrative only.
"""

from datetime import date
from types import SimpleNamespace
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.application.services.data.backtest_preload.known_closes_reader import KnownClosesReader
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMConfiguration,
    STMFeatureConfig,
    STMModelConfig,
    STMTrainingConfig,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_constituent_scorer import (
    STMConstituentScorer,
)
from src.application.services.portfolio_research.stm_decile_cycle import (
    DecileStepResult,
    STMDecileTradingCycle,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_price_history import (
    STMFrontierPriceReader,
)
from src.application.services.dispersion.index_membership import IndexMembership, MembershipChange
from src.application.services.misbuffet.data.market_data_history_service import MarketDataHistoryService
from src.application.services.portfolio_research.decile_portfolios import DecileConfig

MEMBERS = [f"S{i:02d}" for i in range(20)]


def tiny_monthly_stm() -> STMConfiguration:
    cfg = STMConfiguration()
    cfg.features = STMFeatureConfig(return_horizons=(1, 3), vol_lookback=6, macd_combinations=((2, 4),),
                                    macd_price_std_window=4, macd_signal_std_window=6, winsorise_halflife=6,
                                    min_warmup_rows=8, annualisation=12)
    cfg.model = STMModelConfig(model_type="mlp", lookback=3, encoder_length=None, params={})
    cfg.training = STMTrainingConfig(val_days=180, n_epochs=2, early_stopping_rounds=5, batch_size=8,
                                     rolling_window_rows=30)
    cfg.prediction_horizon = 1
    return cfg


def synthetic_world(years: int = 5, seed: int = 11) -> Tuple[pd.DataFrame, IndexMembership]:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2017-01-02", periods=252 * years)
    symbols = MEMBERS + ["NEW"]
    drift = rng.normal(0.0002, 0.0004, len(symbols))
    rets = rng.normal(drift, 0.015, (len(idx), len(symbols)))
    closes = pd.DataFrame(50 * np.exp(np.cumsum(rets, axis=0)), index=idx, columns=symbols)
    membership = IndexMembership("IDX", date(2019, 1, 2), MEMBERS,
                                 [MembershipChange(date(2020, 6, 1), added=("NEW",), removed=("S19",))])
    return closes, membership


def _seed(session, closes: pd.DataFrame, ids: Dict[str, int]) -> None:
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    factor = CompanyShareFactorModel(name="close", group="price", subgroup="TRADES", frequency="1d",
                                     data_type="numeric", source="ibkr", definition="close",
                                     factor_type="company_share_factor")
    session.add(factor)
    session.commit()
    session.bulk_insert_mappings(FactorValueModel, [
        {"factor_id": factor.id, "entity_id": ids[s], "entity_type": "CompanyShare", "date": d.to_pydatetime(),
         "value": repr(float(px))} for s in ids for d, px in closes[s].dropna().items()])
    session.commit()


def synthetic_fundamental(closes: pd.DataFrame):
    """A point-in-time 'fundamental' for model B: each share's trailing 63-day return, known 1 day later
    (computed from closes dated strictly before each date - no look-ahead)."""
    trailing = closes.pct_change(63).shift(1)

    def extra(dates: pd.DatetimeIndex, assets: List[str]) -> Dict[str, pd.DataFrame]:
        return {"fund_synthetic": trailing.reindex(columns=assets).reindex(index=dates, method="ffill")}
    return extra


def run_synthetic_demo(start: date = date(2020, 1, 1), end: date = date(2021, 6, 30), with_b: bool = True,
                       cost_bps: float = 10.0, log=None) -> Tuple[List[DecileStepResult], STMDecileTradingCycle]:
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    closes, membership = synthetic_world()
    engine = create_engine("sqlite:///:memory:")
    ModelBase.metadata.create_all(engine)
    session = Session(engine)
    factory = RepositoryFactory(session)
    ids = {s: 1000 + i for i, s in enumerate(membership.all_constituents())}
    _seed(session, closes, ids)
    history = MarketDataHistoryService(SimpleNamespace(entity_service=SimpleNamespace(repository_factory=factory)))
    reader = KnownClosesReader(start=closes.index[0].date(),
                               frontier=[(STMFrontierPriceReader(history, frequency="1d"), ids)])
    variants = {"A": STMConstituentScorer(tiny_monthly_stm())}
    if with_b:
        variants["B"] = STMConstituentScorer(tiny_monthly_stm(), extra_features=synthetic_fundamental(closes))
    cycle = STMDecileTradingCycle(membership, reader, variants,
                                  DecileConfig(n_deciles=10, transaction_cost_bps=cost_bps), start, end,
                                  traded="A", log=log)
    results = []
    try:
        for d in closes.index:
            if d.date() < start:
                continue
            results.append(cycle.step(d + pd.Timedelta(hours=16)))
    finally:
        session.close()
        engine.dispose()
    return results, cycle
