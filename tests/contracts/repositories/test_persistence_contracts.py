"""
Repository contracts, run unchanged on every backend (tests/persistence.py):

    sqlite      in-memory, foreign keys ON          (fast suite)
    sql_server  dedicated *_test database            (marker sql_server; DB_NAME=..._test)

A difference between the backends here is a real portability defect, not a test problem.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError

from src.domain.entities.factor.factor_value import FactorValue
from src.infrastructure.models.factor.factor import CompanyShareFactorModel
from src.infrastructure.models.finance.holding.holding import HoldingModel
from tests.misbuffet.sqlite_portfolio import T0, SqlitePortfolio
from tests.repositories.repository_checks import (
    REQUIRED_CREATE_KWARGS, factor_repository_classes, factor_round_trip,
)

DAY = 86_400
MON, TUE, WED = datetime(2026, 1, 5), datetime(2026, 1, 6), datetime(2026, 1, 7)


def _fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


@pytest.fixture
def values(backend):
    """FactorValueRepository on the backend, with one raw daily 'close' factor stored."""
    with backend.factory() as (factory, session):
        factor = CompanyShareFactorModel(name="close", group="price", subgroup="ohlc", frequency="1d",
                                         data_type="numeric", source="ibkr", definition="close",
                                         factor_type="company_share_factor")
        session.add(factor)
        session.commit()
        repo = factory.factor_value_local_repo

        def put(entity_id, when, value, entity_type="CompanyShare"):
            stored = repo.add(FactorValue(id=None, factor_id=factor.id, entity_id=entity_id, entity_type=entity_type,
                                          date=when, value=str(value), entity=None))
            assert stored is not None, "add() failed"
            return stored

        yield repo, factor.id, put


class TestFactorValueContract:

    def test_round_trip_keeps_value_text_and_date(self, values):
        repo, fid, put = values
        put(7, MON, "150.123456789")
        got = repo.get_by_factor_entity_date(fid, 7, _fmt(MON), entity_type="CompanyShare")
        assert (got.value, got.date, got.entity_id) == ("150.123456789", MON, 7)

    def test_missing_records_are_none(self, values):
        repo, fid, put = values
        assert repo.get_by_factor_entity_date(fid, 7, _fmt(MON)) is None
        assert repo.get_most_recent_before(fid, 7, _fmt(MON)) is None
        assert repo.get_latest_available_bar(fid, 7, _fmt(MON), bar_seconds=DAY) is None

    def test_entity_type_separates_entities_with_the_same_id(self, values):
        repo, fid, put = values
        put(7, MON, 150, "CompanyShare")
        put(7, MON, 999, "CompanySharePortfolioHoldingModel")
        assert repo.get_by_factor_entity_date(fid, 7, _fmt(MON), entity_type="CompanyShare").value == "150"
        assert repo.get_by_factor_entity_date(fid, 7, _fmt(MON), entity_type="CompanySharePortfolioHoldingModel").value == "999"

    def test_most_recent_before_is_inclusive_and_never_looks_ahead(self, values):
        repo, fid, put = values
        put(7, MON, 1)
        put(7, WED, 3)
        assert repo.get_most_recent_before(fid, 7, _fmt(MON)).value == "1"           # date == target
        assert repo.get_most_recent_before(fid, 7, _fmt(TUE + timedelta(hours=23))).value == "1"
        assert repo.get_most_recent_before(fid, 7, _fmt(WED)).value == "3"

    def test_latest_available_bar_only_returns_closed_bars(self, values):
        repo, fid, put = values
        put(7, MON, 100)                                 # bar stamped at its start
        put(7, TUE, 110)
        assert repo.get_latest_available_bar(fid, 7, _fmt(TUE + timedelta(hours=16)), bar_seconds=DAY).value == "100"
        assert repo.get_latest_available_bar(fid, 7, _fmt(WED), bar_seconds=DAY).value == "110"   # closes exactly now
        assert repo.get_latest_available_bar(fid, 7, _fmt(WED - timedelta(seconds=1)), bar_seconds=DAY).value == "100"

    def test_stale_bars_are_ignored(self, values):
        repo, fid, put = values
        put(7, MON, 100)
        late = _fmt(MON + timedelta(days=30))
        assert repo.get_latest_available_bar(fid, 7, late, bar_seconds=DAY, max_staleness_seconds=3 * DAY) is None
        assert repo.get_latest_available_bar(fid, 7, late, bar_seconds=DAY).value == "100"

    def test_update_and_delete(self, values):
        repo, fid, put = values
        stored = put(7, MON, 100)
        stored.value = "101"
        repo.update(stored)
        assert repo.get_by_factor_entity_date(fid, 7, _fmt(MON)).value == "101"
        assert repo.delete(stored.id) is True
        assert repo.get_by_factor_entity_date(fid, 7, _fmt(MON)) is None

    def test_second_precision_survives_the_round_trip(self, values):
        repo, fid, put = values
        when = datetime(2026, 1, 5, 9, 30, 59)
        put(7, when, 1)
        assert repo.get_by_factor_entity_date(fid, 7, _fmt(when)).date == when

    def test_natural_key_is_unique(self, values):
        """Regression: (factor_id, entity_id, entity_type, date) is unique — a second add stores no second row
        and returns the stored value (the stored value is kept; update replaces it)."""
        repo, fid, put = values
        put(7, MON, 100)
        again = repo.add(FactorValue(id=None, factor_id=fid, entity_id=7, entity_type="CompanyShare",
                                     date=MON, value="101", entity=None))
        assert again is not None and float(again.value) == 100.0
        from src.infrastructure.models.factor.factor_value import FactorValueModel
        assert repo.session.query(FactorValueModel).filter_by(factor_id=fid, entity_id=7).count() == 1

    def test_same_key_for_another_entity_type_is_a_different_value(self, values):
        repo, fid, put = values
        put(7, MON, 100)
        other = repo.add(FactorValue(id=None, factor_id=fid, entity_id=7, entity_type="CompanySharePortfolio",
                                     date=MON, value="5", entity=None))
        assert other is not None and float(other.value) == 5.0


class TestReferentialIntegrity:

    def test_holding_for_a_missing_asset_is_rejected(self, backend):
        with backend.factory() as (factory, session):
            session.add(HoldingModel(asset_id=999_999, container_id=999_998, start_date=T0))
            with pytest.raises((IntegrityError, DBAPIError)):
                session.commit()
            session.rollback()


    def test_company_share_needs_no_placeholder_references(self, backend):
        """BI-008 (was a strict xfail): exchange, company, country, industry and sector are real rows."""
        from src.infrastructure.models.finance.company import CompanyModel
        from src.infrastructure.models.finance.exchange import ExchangeModel
        from src.infrastructure.models.industry import IndustryModel
        from src.infrastructure.models.country import CountryModel
        from src.infrastructure.models.sector import SectorModel
        with backend.factory() as (factory, session):
            share = factory.company_share_local_repo._create_or_get("NVDA")
            assert share is not None
            company = session.get(CompanyModel, share.company_id)
            exchange = session.get(ExchangeModel, share.exchange_id)
            industry = session.get(IndustryModel, company.industry_id)
            assert session.get(CountryModel, company.country_id) is not None
            assert session.get(CountryModel, exchange.country_id) is not None
            assert session.get(SectorModel, industry.sector_id) is not None


class TestOrderBookingContract:

    @pytest.fixture
    def portfolio(self, backend):
        p = SqlitePortfolio(engine=backend.engine)
        yield p
        p.close()

    def test_buy_books_order_transaction_position_and_cash(self, portfolio):
        assert portfolio.trade("AAPL", 10, 150.0)
        assert portfolio.qty("AAPL") == 10
        assert portfolio.cash() == 98_500.0
        assert (len(portfolio.orders()), len(portfolio.transactions())) == (2, 2)
        assert {t.date for t in portfolio.transactions()} == {T0}

    def test_sell_after_buy_and_reuse_of_the_holding(self, portfolio):
        portfolio.trade("AAPL", 10, 150.0)
        portfolio.trade("AAPL", -4, 160.0, when=T0 + timedelta(days=1))
        assert (portfolio.qty("AAPL"), portfolio.cash()) == (6, 98_500.0 + 640.0)
        aapl = portfolio.factory.company_share_local_repo.get_by_symbol("AAPL")
        assert portfolio.session.query(HoldingModel).filter(HoldingModel.asset_id == aapl.id).count() == 1

    def test_portfolio_registration_is_idempotent(self, portfolio):
        again = portfolio.upm.register_portfolio_with_config({"name": "TEST", "initial_cash": 100_000.0})
        assert again.id == portfolio.portfolio.id
        assert portfolio.cash() == 100_000.0


class TestFactorRepositoryContract:

    def test_every_factor_repository_round_trips(self, backend):
        problems = []
        for _, cls in factor_repository_classes():
            with backend.factory() as (factory, session):
                problem = factor_round_trip(cls, session, factory)
            if problem:
                problems.append(f"{cls.__name__}: {problem}")
        assert problems == []
