"""
Synthetic demo of the monthly model-filtered dispersion (no IBKR, no SQL Server).

Runs the SAME DispersionTradingCycle the Misbuffet algorithm runs, on synthetic daily closes: the members' and the
ETF's closes are stored in an in-memory SQLite database as raw TRADES `close` factors of frequency '1d'
(company_share_factor / etf_share_factor, read through the MarketDataHistoryService frontier: a close dated D is
known from D+1 00:00); one member (``fallback_member``) comes from an in-memory PriceHistoryPort instead, as a member
IBKR no longer lists comes from the file cache in the engine. The index is equal-share (price-weighted) over a small
membership with one change. The STM model is shrunk for speed. Results are illustrative only.
"""

from datetime import date
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMConfiguration,
    STMModelConfig,
    STMTrainingConfig,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_price_history import (
    STMFrontierPriceReader,
)
from src.application.services.dispersion.dispersion_portfolio_construction_service import (
    WHOLE,
    DispersionPortfolioConstructionService,
)
from src.application.services.dispersion.dispersion_trading_cycle import (
    DispersionStepResult,
    DispersionTradingCycle,
    KnownClosesReader,
)
from src.application.services.dispersion.index_membership import IndexMembership, MembershipChange
from src.application.services.dispersion.model_selection import ModelFilterConfig
from src.application.services.dispersion.modelled_option_pricing import ModelledOptionPricer, OptionModelConfig
from src.application.services.dispersion.screen_config import DispersionScreenConfig
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_constituent_scorer import STMConstituentScorer
from src.application.services.misbuffet.data.market_data_history_service import MarketDataHistoryService
from src.domain.ports.finance.dispersion.price_history_port import PriceHistoryPort


class FramePrices(PriceHistoryPort):
    """A PriceHistoryPort over a close frame (dates x symbols)."""

    def __init__(self, frame: pd.DataFrame):
        self.frame = frame

    def daily_closes(self, underlying, start, end):
        if underlying.symbol not in self.frame:
            return {}
        s = self.frame[underlying.symbol].dropna()
        return {d.date(): float(v) for d, v in s.items() if start <= d.date() <= end}


def tiny_stm() -> STMConfiguration:
    cfg = STMConfiguration()
    cfg.model = STMModelConfig(model_type="mlp", lookback=10, encoder_length=None, params={})
    f = cfg.features
    f.return_horizons, f.macd_combinations = (1, 5, 21), ((8, 24),)
    f.macd_price_std_window, f.macd_signal_std_window, f.vol_lookback = 21, 42, 20
    f.min_warmup_rows, f.winsorise_halflife = 70, 42
    cfg.training = STMTrainingConfig(val_days=60, n_epochs=2, early_stopping_rounds=5, batch_size=32,
                                     rolling_window_rows=200)
    cfg.prediction_horizon = 5
    return cfg


def synthetic_world(n_days: int = 700, seed: int = 4, start: str = "2019-06-03"
                    ) -> Tuple[pd.DataFrame, IndexMembership]:
    """An equal-share index of A, B, C (C replaced by D on 2021-06-01) and its ETF (= sum of prices / 10)."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, periods=n_days)
    prices = {s: 50 * (i + 1) * np.exp(np.cumsum(rng.normal(0.0003, 0.015, n_days))) for i, s in enumerate("ABCD")}
    closes = pd.DataFrame(prices, index=idx)
    m = IndexMembership("ETF", date(2020, 1, 2), ["A", "B", "C"],
                        [MembershipChange(date(2021, 6, 1), added=("D",), removed=("C",))])
    etf = [closes.loc[d, m.members_at(d.date()) if d.date() >= m.base_date else ["A", "B", "C"]].sum() / 10
           for d in idx]
    closes["ETF"] = etf
    return closes[["ETF", "A", "B", "C", "D"]], m


def _seed_closes(session, closes: pd.DataFrame, ids: Dict[str, int], model_class, factor_type: str,
                 entity_type: str) -> None:
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    factor = model_class(name="close", group="price", subgroup="TRADES", frequency="1d", data_type="numeric",
                         source="ibkr", definition="close", factor_type=factor_type)
    session.add(factor)
    session.commit()
    rows = [{"factor_id": factor.id, "entity_id": ids[t], "entity_type": entity_type,
             "date": d.to_pydatetime(), "value": repr(float(px))}
            for t in ids for d, px in closes[t].dropna().items()]
    session.bulk_insert_mappings(FactorValueModel, rows)
    session.commit()


def run_synthetic_demo(start: date = date(2020, 6, 1), end: date = date(2022, 3, 31), n_days: int = 700,
                       stm: Optional[STMConfiguration] = None, traded: str = "model_filtered",
                       fallback_member: Optional[str] = "C", log=None) -> Tuple[List[DispersionStepResult], DispersionTradingCycle, pd.DataFrame]:
    """(step results, the cycle, the closes). One step a business day at 16:00, as the engine's clock."""
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.repository_factory import RepositoryFactory

    closes, membership = synthetic_world(n_days)
    engine = create_engine("sqlite:///:memory:")
    ModelBase.metadata.create_all(engine)
    session = Session(engine)
    factory = RepositoryFactory(session)
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel, ETFShareFactorModel
    ids = {s: 1000 + i for i, s in enumerate(membership.all_constituents()) if s != fallback_member}
    etf_ids = {membership.etf: 2000}
    _seed_closes(session, closes, ids, CompanyShareFactorModel, "company_share_factor", "CompanyShare")
    _seed_closes(session, closes, etf_ids, ETFShareFactorModel, "etf_share_factor", "ETFShare")
    history = MarketDataHistoryService(SimpleNamespace(entity_service=SimpleNamespace(repository_factory=factory)))
    reader = KnownClosesReader(
        start=closes.index[0].date(),
        frontier=[(STMFrontierPriceReader(history, frequency="1d"), ids),
                  (STMFrontierPriceReader(history, factor_type="etf_share_factor", frequency="1d"), etf_ids)],
        fallback=FramePrices(closes), fallback_symbols=[fallback_member] if fallback_member else [])
    cycle = DispersionTradingCycle(
        membership, reader, STMConstituentScorer(stm or tiny_stm()), ModelledOptionPricer(OptionModelConfig(vol_window=21)),
        DispersionPortfolioConstructionService(WHOLE), ModelFilterConfig(minimum_model_score=0.0),
        DispersionScreenConfig(target_dte=30, min_dte=20, max_dte=60), start=start, end=end, traded=traded,
        log=log)
    results = []
    try:
        for d in closes.index:
            if d.date() < start:
                continue
            results.append(cycle.step(d + pd.Timedelta(hours=16)))
    finally:
        session.close()
        engine.dispose()
    return results, cycle, closes
