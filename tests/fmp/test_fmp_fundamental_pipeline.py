"""End to end on in-memory SQLite with a fake FMP: FMP statements -> FMP repositories -> raw fundamental series
(stamped at publication) -> FactorValueResolutionService (family 'fmp', point in time) -> calculated profitability /
leverage / growth / valuation factors -> stored factor values. Nothing is downloaded."""

from datetime import datetime, timedelta

import pytest

from src.application.services.data.entities.factor.factor_value_resolution_service import (
    FactorValueResolutionService,
)
from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
    CompanyShareFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_growth_factor import (
    CompanyShareFundamentalGrowthFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_leverage_factor import (
    CompanyShareFundamentalLeverageFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_profitability_factor import (
    CompanyShareFundamentalProfitabilityFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_valuation_factor import (
    CompanyShareFundamentalValuationFactor,
)
from src.infrastructure.models.factor.factor_value import FactorValueModel
from src.infrastructure.repositories.fmp_repo.fmp_client import FMPClient
from tests.fmp import fake_fmp
from tests.fmp.fake_fmp import FakeSession, accepted, balance, cash_flow, income
from tests.misbuffet.sqlite_portfolio import SqlitePortfolio

T = datetime(2025, 12, 31, 12, 0)          # Q3 2025 (index 10) is public, Q4 2025 (index 11) is not yet


@pytest.fixture
def world():
    p = SqlitePortfolio(cash=0.0, shares=(fake_fmp.SYMBOL,))
    session = FakeSession()
    p.factory.create_fmp_repositories(FMPClient("test-key", session=session, min_interval=0))
    share = p.factory.get_local_repository("CompanyShare").get_by_symbol(fake_fmp.SYMBOL)
    service = FactorValueResolutionService(factory=p.factory)
    yield p, share, service, session
    p.close() if hasattr(p, "close") else None


def raw(p, name, statement="income_statement", frequency="1q"):
    return p.factory.get_local_repository("CompanyShareFactor")._create_or_get(
        CompanyShareFactor, name, group="fundamental", subgroup=statement, frequency=frequency, source="fmp")


def calc(p, cls, name, frequency="1q"):
    return p.factory.get_local_repository(cls.__name__)._create_or_get(cls, name, frequency=frequency)


def value(service, factor, share, when):
    fv = service.resolve_factor_value(factor, share, when)
    return None if fv is None else float(fv.value)


def test_raw_statement_values_are_served_as_of_their_publication(world):
    p, share, service, session = world
    revenue = raw(p, "revenue")
    assert value(service, revenue, share, T) == income(10)["revenue"]
    # one request per fiscal quarter for the whole history, then everything comes from the store
    assert [c[1]["period"] for c in session.calls] == ["Q1", "Q2", "Q3", "Q4"]
    published = accepted(10)
    assert value(service, revenue, share, published - timedelta(seconds=1)) == income(9)["revenue"]
    assert value(service, revenue, share, published) == income(10)["revenue"]
    assert value(service, revenue, share, accepted(0) - timedelta(days=1)) is None         # nothing public yet
    assert value(service, revenue, share, accepted(11) + timedelta(days=250)) is None      # too old (max age)
    assert value(service, raw(p, "totalDebt", "balance_sheet"), share, T) == 1000.0
    assert value(service, raw(p, "freeCashFlow", "cash_flow"), share, T) == cash_flow(10)["freeCashFlow"]
    assert value(service, raw(p, "revenue", frequency="1y"), share, T) == sum(income(i)["revenue"] for i in range(4, 8))
    assert len(session.calls) == 4 + 4 + 4 + 1         # quarters of the three statements, the income statement's FY


def test_the_filings_data_are_stored_with_the_values(world):
    p, share, service, _ = world
    value(service, raw(p, "revenue"), share, T)
    period_end = raw(p, "date")
    rows = (p.session.query(FactorValueModel)
            .filter_by(factor_id=period_end.id, entity_id=share.id, entity_type="CompanyShare").all())
    stamps = {r.date.replace(tzinfo=None): r.value for r in rows}
    assert stamps[accepted(10)] == "2025-09-30" and len(stamps) == 12
    accepted_rows = (p.session.query(FactorValueModel)
                     .filter_by(factor_id=raw(p, "acceptedDate").id, entity_id=share.id).all())
    assert all(r.value == r.date.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S") for r in accepted_rows)
    assert raw(p, "reportedCurrency").data_type == "string" and raw(p, "revenue").source == "fmp"


def test_profitability_and_leverage_factors_resolve_through_the_pipeline(world):
    p, share, service, _ = world
    margin = calc(p, CompanyShareFundamentalProfitabilityFactor, "gross_margin")
    i = income(10)
    assert value(service, margin, share, T) == pytest.approx(i["grossProfit"] / i["revenue"])
    roe = calc(p, CompanyShareFundamentalProfitabilityFactor, "roe")
    equity = (balance(9)["totalStockholdersEquity"] + balance(10)["totalStockholdersEquity"]) / 2
    assert value(service, roe, share, T) == pytest.approx(i["netIncome"] / equity)
    leverage = calc(p, CompanyShareFundamentalLeverageFactor, "net_debt_to_ebitda_ttm")
    assert value(service, leverage, share, T) == pytest.approx(700.0 / sum(income(q)["ebitda"] for q in range(7, 11)))
    annual = calc(p, CompanyShareFundamentalProfitabilityFactor, "gross_margin", frequency="1y")
    year = [income(q) for q in range(4, 8)]
    assert value(service, annual, share, T) == pytest.approx(sum(y["grossProfit"] for y in year) /
                                                            sum(y["revenue"] for y in year))
    stored = p.session.query(FactorValueModel).filter_by(factor_id=margin.id, entity_id=share.id).all()
    assert [r.date.replace(tzinfo=None) for r in stored] == [T]                    # a calculated value at its time


def test_growth_uses_consecutive_published_periods(world):
    p, share, service, _ = world
    yoy = calc(p, CompanyShareFundamentalGrowthFactor, "revenue_growth_yoy")
    assert value(service, yoy, share, T) == pytest.approx(income(10)["revenue"] / income(6)["revenue"] - 1)
    ttm = calc(p, CompanyShareFundamentalGrowthFactor, "revenue_growth_ttm")
    assert value(service, ttm, share, T) == pytest.approx(
        sum(income(q)["revenue"] for q in range(7, 11)) / sum(income(q)["revenue"] for q in range(3, 7)) - 1)
    # eight quarters are not public yet in mid 2024: no TTM growth over a shorter window
    assert value(service, ttm, share, datetime(2024, 9, 1)) is None
    annual = calc(p, CompanyShareFundamentalGrowthFactor, "total_debt_growth", frequency="1y")
    assert value(service, annual, share, T) == pytest.approx(0.0)


def test_a_missing_quarter_gives_no_growth_over_it():
    p = SqlitePortfolio(cash=0.0, shares=(fake_fmp.SYMBOL,))
    hole = fake_fmp.QUARTER_ENDS[9].isoformat()                      # Q2 2025 never published
    session = FakeSession(data=lambda endpoint, period: [r for r in fake_fmp.rows(endpoint, period) if r["date"] != hole])
    p.factory.create_fmp_repositories(FMPClient("k", session=session, min_interval=0))
    share = p.factory.get_local_repository("CompanyShare").get_by_symbol(fake_fmp.SYMBOL)
    service = FactorValueResolutionService(factory=p.factory)
    qoq = calc(p, CompanyShareFundamentalGrowthFactor, "revenue_growth")
    assert value(service, qoq, share, T) is None                    # Q3 over Q1: not one quarter
    assert value(service, calc(p, CompanyShareFundamentalProfitabilityFactor, "gross_margin"), share, T) is not None


def test_valuation_combines_the_statements_with_the_close(world):
    p, share, service, _ = world
    close = p.factory.get_local_repository("CompanyShareFactor")._create_or_get(
        CompanyShareFactor, "close", group="price", subgroup="TRADES", frequency="1d", source="ibkr")
    p.factory.get_local_repository("FactorValue").add_bulk(
        [FactorValue(id=None, factor_id=close.id, entity=None, entity_id=share.id, entity_type="CompanyShare",
                     date=datetime(2025, 12, 30), value="50.0")])
    ey = calc(p, CompanyShareFundamentalValuationFactor, "earnings_yield_ttm")
    eps = sum(income(q)["epsDiluted"] for q in range(7, 11))
    assert value(service, ey, share, T) == pytest.approx(eps / 50.0)


def test_without_fmp_enabled_nothing_is_requested_and_there_is_no_value():
    p = SqlitePortfolio(cash=0.0, shares=(fake_fmp.SYMBOL,))
    assert p.factory._available_repository_families["fmp"] is False and p.factory.factor_value_fmp_repo is None
    share = p.factory.get_local_repository("CompanyShare").get_by_symbol(fake_fmp.SYMBOL)
    service = FactorValueResolutionService(factory=p.factory)
    assert value(service, calc(p, CompanyShareFundamentalProfitabilityFactor, "gross_margin"), share, T) is None


def test_a_symbol_outside_the_subscription_is_asked_once_and_gives_no_value():
    p = SqlitePortfolio(cash=0.0, shares=("ZZZZ",))
    session = FakeSession()
    p.factory.create_fmp_repositories(FMPClient("k", session=session, min_interval=0))
    share = p.factory.get_local_repository("CompanyShare").get_by_symbol("ZZZZ")
    service = FactorValueResolutionService(factory=p.factory)
    revenue = raw(p, "revenue")
    assert value(service, revenue, share, T) is None and value(service, revenue, share, T) is None
    assert len(session.calls) == 1                                    # the 402 is not asked again in the session
