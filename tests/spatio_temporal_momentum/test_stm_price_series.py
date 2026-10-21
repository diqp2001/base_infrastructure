"""BI-036: the STM close panel takes ONE close series per asset — MIDPOINT before TRADES, legacy 'ohlc' last."""

import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_price_history import (
    STMPriceHistoryReader,
)
from src.infrastructure.models.factor.factor import CompanyShareFactorModel
from src.infrastructure.models.factor.factor_value import FactorValueModel
from tests.spatio_temporal_momentum.helpers import make_factory, seed_closes, synthetic_closes

IDS = {"AAA": 1, "BBB": 2}


def add_series(session, subgroup, closes, ticker, shift):
    f = CompanyShareFactorModel(name="close", group="price", subgroup=subgroup, frequency="1d", data_type="numeric",
                                source="ibkr", definition=f"close {subgroup}", factor_type="company_share_factor")
    session.add(f)
    session.commit()
    for d, px in closes[ticker].items():
        session.add(FactorValueModel(factor_id=f.id, entity_id=IDS[ticker], entity_type="CompanyShare",
                                     date=pd.Timestamp(d).to_pydatetime(), value=repr(float(px) + shift)))
    session.commit()


def test_each_asset_reads_one_series_in_preference_order():
    factory, session, engine = make_factory()
    try:
        closes = synthetic_closes(30, assets=list(IDS))
        seed_closes(session, closes, IDS)                              # legacy 'ohlc' for both assets
        add_series(session, "TRADES", closes, "AAA", shift=1.0)
        add_series(session, "MIDPOINT", closes, "AAA", shift=0.5)       # AAA: MIDPOINT wins over TRADES and ohlc
        add_series(session, "TRADES", closes.iloc[:10], "BBB", shift=2.0)   # BBB: TRADES (short) wins over ohlc
        panel = STMPriceHistoryReader(factory).load_close_panel({v: k for k, v in IDS.items()})
        assert (panel["AAA"] - (closes["AAA"].values + 0.5)).abs().max() < 1e-9
        bbb = panel["BBB"].dropna()
        assert len(bbb) == 10 and (bbb - (closes["BBB"].iloc[:10].values + 2.0)).abs().max() < 1e-9
    finally:
        session.close()
        engine.dispose()
