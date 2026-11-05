"""Dispersion screener P.02: ETFShare and the ShareOption hierarchy (CompanyShareOption, ETFShareOption).
In-memory SQLite only."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import CompanyShareOption
from src.domain.entities.finance.financial_assets.derivatives.option.etf_share_option import ETFShareOption
from src.domain.entities.finance.financial_assets.derivatives.option.share_option import ShareOption
from src.domain.entities.finance.financial_assets.share.etf_share.etf_share import ETFShare
from src.domain.entities.finance.financial_assets.share.share import Share
from src.infrastructure.models import ModelBase
from src.infrastructure.repositories.repository_factory import RepositoryFactory


@pytest.fixture
def factory():
    engine = create_engine("sqlite:///:memory:")
    ModelBase.metadata.create_all(engine)
    session = Session(engine)
    yield RepositoryFactory(session)
    session.close()
    engine.dispose()


def test_domain_hierarchy_and_etf_flags():
    assert issubclass(CompanyShareOption, ShareOption) and issubclass(ETFShareOption, ShareOption)
    assert issubclass(ETFShare, Share)
    option = ETFShareOption(id=None, name="XLU call", symbol="XLU   261218C00080000", underlying_asset_id=7,
                            exchange_id=1, option_type="call", strike_price=80, multiplier=100, expiry="20261218")
    assert (option.strike_price, option.multiplier, option.expiry, option.exchange_id) == (80, 100, "20261218", 1)
    plain = ETFShare(id=None, symbol="XLU", currency_id=1, exchange_id=1)
    assert not (plain.is_leveraged or plain.is_inverse or plain.is_synthetic)
    assert ETFShare(id=None, symbol="SDS", currency_id=1, exchange_id=1, leverage_factor=-2.0).is_inverse
    assert ETFShare(id=None, symbol="SSO", currency_id=1, exchange_id=1, leverage_factor=2.0).is_leveraged
    assert ETFShare(id=None, symbol="X", currency_id=1, exchange_id=1, replication="Synthetic").is_synthetic


def test_etf_share_is_stored_once_with_its_attributes(factory):
    repo = factory.get_local_repository("ETFShare")
    etf = repo._create_or_get("XLU", name="Utilities Select Sector SPDR", issuer="State Street",
                              asset_class="Equity", replication="physical", exchange_name="NYSE")
    assert etf is not None and etf.id is not None
    again = repo._create_or_get("XLU")
    assert again.id == etf.id and len(repo.get_all()) == 1
    stored = repo.get_by_id(etf.id)
    assert (stored.symbol, stored.issuer, stored.asset_class, stored.leverage_factor) == (
        "XLU", "State Street", "Equity", 1.0)
    assert [e.symbol for e in repo.get_by_issuer("State Street")] == ["XLU"]


def test_etf_and_company_share_options_stay_in_their_own_tables(factory):
    etf = factory.get_local_repository("ETFShare")._create_or_get("XLU", exchange_name="NYSE")
    share = factory.get_local_repository("CompanyShare")._create_or_get("NEE", exchange_name="NYSE")
    etf_options = factory.get_local_repository("ETFShareOption")
    company_options = factory.get_local_repository("CompanyShareOption")

    etf_call = etf_options._create_or_get(symbol="XLU   261218C00080000", option_type="call",
                                          underlying_asset_id=etf.id, strike_price=80, expiry="20261218",
                                          multiplier=100)
    nee_call = company_options._create_or_get(symbol="NEE   261218C00080000", option_type="call",
                                              underlying_asset_id=share.id)
    assert isinstance(etf_call, ETFShareOption) and isinstance(nee_call, CompanyShareOption)
    assert (float(etf_call.strike_price), etf_call.expiry, float(etf_call.multiplier)) == (80.0, "20261218", 100.0)
    assert etf_call.exchange_id == etf.exchange_id                     # the underlying's exchange by default

    # a lookup never returns the other type's option, and the underlying must have the right type
    assert company_options.get_by_symbol("XLU   261218C00080000") is None
    assert etf_options.get_by_symbol("NEE   261218C00080000") is None
    assert etf_options._create_or_get(symbol="BAD", underlying_asset_id=share.id) is None
    assert [o.id for o in etf_options.get_by_underlying_id(etf.id)] == [etf_call.id]
    assert [o.id for o in company_options.get_by_company_share_id(share.id)] == [nee_call.id]

    related = etf_options.get_related_entities(etf_call.id)
    assert any(isinstance(r, ETFShare) and r.id == etf.id for r in related)
