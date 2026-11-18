"""The IBKR side of ETFShare (recreated 2026-11-16): the Misbuffet MarketDataService finds an IBKR repository for the
ETF share and for its factors, so an ETF's bars are imported like a company share's. Fake IBKR client, in-memory
SQLite."""

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_factor import ETFShareFactor
from src.domain.entities.finance.financial_assets.share.etf_share.etf_share import ETFShare
from src.infrastructure.repositories.repository_factory import RepositoryFactory


class FakeBroker:
    def __init__(self):
        self.asked = []

    def get_contract_details(self, contract, timeout=15):
        self.asked.append((contract.symbol, contract.secType, contract.exchange, contract.currency))
        return [{"long_name": "SPDR DOW JONES INDUSTRIAL AVERAGE ETF TRUST", "currency": "USD", "exchange": "ARCA"}]


@pytest.fixture()
def factory():
    from src.infrastructure.models import ModelBase
    engine = create_engine("sqlite:///:memory:")
    ModelBase.metadata.create_all(engine)
    session = Session(engine)
    broker = FakeBroker()
    with patch.object(RepositoryFactory, "create_ibkr_client", return_value=broker):
        f = RepositoryFactory(session, ibkr_client=broker)
    f.create_ibkr_repositories(broker)
    yield f, broker
    session.close()


def test_the_factory_has_ibkr_repositories_for_the_etf_share_and_its_factors(factory):
    f, _ = factory
    assert type(f.get_ibkr_repository(ETFShare)).__name__ == "IBKRETFShareRepository"
    assert type(f.get_ibkr_repository(ETFShareFactor)).__name__ == "IBKRETFShareFactorRepository"
    assert f.get_ibkr_repository("ETFShare") is f.get_ibkr_repository(ETFShare)


def test_the_etf_share_is_created_from_ibkr_contract_details_once(factory):
    f, broker = factory
    repo = f.get_ibkr_repository(ETFShare)
    with patch.object(type(repo), "_get_or_create_exchange",
                      lambda self, code: f.get_local_repository("Exchange")._create_or_get(code)
                      if hasattr(f.get_local_repository("Exchange"), "_create_or_get") else None):
        dia = repo._create_or_get("DIA")
    assert isinstance(dia, ETFShare) and dia.symbol == "DIA" and dia.id is not None
    assert broker.asked == [("DIA", "STK", "SMART", "USD")]           # an ETF is a stock at IBKR
    assert repo._create_or_get("DIA").id == dia.id and len(broker.asked) == 1     # stored: not asked again
    hist = repo._fetch_historical_contract("dia")
    assert (hist.symbol, hist.secType, hist.exchange, hist.currency) == ("DIA", "STK", "SMART", "USD")


def test_the_etf_share_factor_is_the_raw_trades_series(factory):
    f, _ = factory
    close = f.get_ibkr_repository(ETFShareFactor)._create_or_get("close", group="price", subgroup="TRADES",
                                                                  frequency="1d")
    assert isinstance(close, ETFShareFactor) and close.name == "close" and close.subgroup == "TRADES"
    again = f.get_ibkr_repository(ETFShareFactor)._create_or_get("close", group="price", subgroup="TRADES",
                                                                  frequency="1d")
    assert again.id == close.id


def test_the_etf_share_option_is_an_ibkr_opt_contract_on_the_etf(factory):
    from src.domain.entities.finance.financial_assets.derivatives.option.etf_share_option import ETFShareOption
    f, _ = factory
    repo = f.get_ibkr_repository(ETFShareOption)
    assert type(repo).__name__ == "IBKRETFShareOptionRepository"
    c = repo._fetch_historical_contract("DIA   210219C00300000")
    assert (c.symbol, c.secType, c.right, c.strike, c.lastTradeDateOrContractMonth) == (
        "DIA", "OPT", "C", 300.0, "20210219")


def test_the_etf_share_option_raw_series_has_an_ibkr_factor_repository(factory):
    from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import (
        ETFShareOptionFactor,
    )
    f, _ = factory
    repo = f.get_ibkr_repository(ETFShareOptionFactor)
    assert type(repo).__name__ == "IBKRETFShareOptionFactorRepository"
    mid = repo._create_or_get("close", group="price", subgroup="MIDPOINT", frequency="1d")
    assert isinstance(mid, ETFShareOptionFactor) and mid.subgroup == "MIDPOINT"
