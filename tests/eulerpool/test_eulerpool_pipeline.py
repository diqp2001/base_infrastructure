"""Eulerpool in the SAME FactorValue pipeline as IBKR and FMP (in-memory SQLite, fake providers - nothing is
downloaded):

    Eulerpool API -> EulerpoolClient -> Eulerpool statement repositories (FinancialStatementSourcePort,
    StatementRecord) -> the shared StatementFactorValueRepository (FactorValueProviderPort, family 'eulerpool',
    reached through RepositoryFactory.factor_value_provider) -> raw CompanyShareFactor series (source 'eulerpool')
    -> DependencySpec dependencies -> calculate() -> FactorValueRepository

No factor, resolver or factor value code is specific to Eulerpool: the same calculated factors read FMP or Eulerpool
(STATEMENT_SOURCES, one provider per value, FMP first)."""

from datetime import datetime, timedelta
from pathlib import Path

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
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_profitability_factor import (
    CompanyShareFundamentalProfitabilityFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_statement_item_factor import (
    CompanyShareFundamentalStatementItemFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_valuation_factor import (
    CompanyShareFundamentalValuationFactor,
)
from src.domain.entities.factor.observation_quality import ObservationRef
from src.domain.ports.factor.factor_value_provider_port import FactorValueProviderPort
from src.infrastructure.models.factor.factor_value import FactorValueModel
from src.infrastructure.repositories.eulerpool_repo.eulerpool_client import EulerpoolClient
from src.infrastructure.repositories.fmp_repo.fmp_client import FMPClient
from src.infrastructure.repositories.fundamental_provider.statement_factor_value_repository import (
    StatementFactorValueRepository,
)
from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository
from tests.eulerpool import fake_eulerpool
from tests.eulerpool.fake_eulerpool import KEY, FakeSession, original_filed
from tests.fmp import fake_fmp
from tests.fmp.fake_fmp import QUARTER_ENDS, balance, cash_flow, income
from tests.misbuffet.sqlite_portfolio import SqlitePortfolio

T = datetime(2025, 12, 31, 12, 0)          # Q3 2025 (index 10) is public, Q4 2025 (index 11) is not yet
SRC = Path(__file__).resolve().parents[2] / "src"


def eulerpool_client(session=None):
    return EulerpoolClient(KEY, session=session or FakeSession(), min_interval=0, sleep=lambda s: None)


def make_world(eulerpool=True, fmp_symbols=None):
    p = SqlitePortfolio(cash=0.0, shares=(fake_eulerpool.SYMBOL,))
    session = FakeSession()
    if eulerpool:
        p.factory.create_eulerpool_repositories(eulerpool_client(session))
    fmp_session = None
    if fmp_symbols is not None:
        fmp_session = fake_fmp.FakeSession(symbols=fmp_symbols)
        p.factory.create_fmp_repositories(FMPClient("fmp-key", session=fmp_session, min_interval=0))
    share = p.factory.get_local_repository("CompanyShare").get_by_symbol(fake_eulerpool.SYMBOL)
    return p, share, FactorValueResolutionService(factory=p.factory), session, fmp_session


@pytest.fixture
def world():
    p, share, service, session, _ = make_world()
    yield p, share, service, session
    p.close()


def raw(p, name, statement="income_statement", frequency="1q", source="eulerpool"):
    return p.factory.get_local_repository("CompanyShareFactor")._create_or_get(
        CompanyShareFactor, name, group="fundamental", subgroup=statement, frequency=frequency, source=source)


def calc(p, cls, name, frequency="1q"):
    return p.factory.get_local_repository(cls.__name__)._create_or_get(cls, name, frequency=frequency)


def value(service, factor, share, when):
    fv = service.resolve_factor_value(factor, share, when)
    return None if fv is None else float(fv.value)


def stored(p, factor, share):
    return (p.session.query(FactorValueModel)
            .filter_by(factor_id=factor.id, entity_id=share.id, entity_type="CompanyShare")
            .order_by(FactorValueModel.date).all())


def lineage_sources(p, factor, share, when):
    lineage = p.factory.observation_provenance_local_repo.get(ObservationRef(factor.id, "CompanyShare", share.id, when))
    repo = p.factory.factor_local_repo
    return {repo.get_by_id(ref.factor_id).source for ref in lineage.inputs}, lineage


# -- RepositoryFactory --

def test_the_factory_serves_the_eulerpool_family_through_the_shared_provider(world):
    p, _, _, _ = world
    provider = p.factory.factor_value_provider("eulerpool")
    assert isinstance(provider, StatementFactorValueRepository) and isinstance(provider, FactorValueProviderPort)
    assert provider.source == "eulerpool" and p.factory.provider_family_enabled("eulerpool", "eulerpool")
    assert {"FactorValue", "Fundamentals", "IncomeStatement", "BalanceSheet", "CashFlowStatement"} <= set(
        p.factory._eulerpool_repositories)
    fresh = SqlitePortfolio(cash=0.0, shares=("X",))
    assert fresh.factory.factor_value_provider("eulerpool") is None                        # off until enabled
    assert fresh.factory.provider_family_enabled("eulerpool", "eulerpool") is False
    fresh.close()


def test_no_provider_name_in_the_resolver_nor_an_eulerpool_factor_value_class():
    resolver = (SRC / "application/services/data/entities/factor/factor_value_resolution_service.py").read_text(
        encoding="utf-8")
    assert "'eulerpool'" not in resolver and '"eulerpool"' not in resolver and "== 'fmp'" not in resolver
    names = {f.stem for f in (SRC / "infrastructure/repositories/eulerpool_repo").rglob("*.py")}
    assert not any("factor_value" in n for n in names)


# -- raw observation -> FactorValue --

def test_a_raw_eulerpool_value_reaches_the_factor_value_store(world):
    p, share, service, session = world
    revenue = raw(p, "revenue")
    assert value(service, revenue, share, T) == income(10)["revenue"]
    rows = stored(p, revenue, share)
    assert len(rows) == 12                       # the whole history at once, then read from the store
    assert len(session.calls) == 4               # FY, Q1, Q2, Q3 of the income statement
    # each quarter at its publication: the latest with its own filing, the older ones at the SEC deadline bound
    stamps = [r.date.replace(tzinfo=None) for r in rows]
    assert stamps[10] == datetime.combine(original_filed(10) + timedelta(days=1), datetime.min.time())
    assert stamps[0] == datetime.combine(QUARTER_ENDS[0] + timedelta(days=51), datetime.min.time())
    assert value(service, revenue, share, T) == income(10)["revenue"] and len(session.calls) == 4
    usd = p.factory.get_local_repository("Currency").get_by_iso_code("USD")
    if usd is not None:
        assert {r.currency_id for r in rows} == {usd.id}
    filing = {n: next(r.value for r in stored(p, raw(p, n), share) if r.date.replace(tzinfo=None) == stamps[10])
              for n in ("date", "period", "fiscalYear", "reportedCurrency", "cik")}
    assert filing == {"date": "2025-09-30", "period": "Q3", "fiscalYear": "2025", "reportedCurrency": "USD",
                      "cik": "0000000001"}


def test_nothing_is_known_before_its_publication(world):
    p, share, service, _ = world
    revenue = raw(p, "revenue")
    published = datetime.combine(original_filed(10) + timedelta(days=1), datetime.min.time())
    assert value(service, revenue, share, published - timedelta(seconds=1)) == income(9)["revenue"]
    assert value(service, revenue, share, published) == income(10)["revenue"]


# -- dependencies: Revenue + GrossProfit -> GrossMargin, OCF + capex -> FCF --

def test_gross_margin_from_eulerpool_revenue_and_gross_profit(world):
    p, share, service, _ = world
    margin = calc(p, CompanyShareFundamentalProfitabilityFactor, "gross_margin")
    assert value(service, margin, share, T) == pytest.approx(income(10)["grossProfit"] / income(10)["revenue"])
    sources, lineage = lineage_sources(p, margin, share, T)
    assert sources == {"eulerpool"}
    assert {ref.factor_id for ref in lineage.inputs} == {raw(p, "revenue").id, raw(p, "grossProfit").id}
    assert margin.source == "calculated"


def test_free_cash_flow_and_growth_from_eulerpool(world):
    p, share, service, _ = world
    fcf = calc(p, CompanyShareFundamentalStatementItemFactor, "free_cash_flow")
    assert value(service, fcf, share, T) == pytest.approx(cash_flow(10)["freeCashFlow"])
    ttm = calc(p, CompanyShareFundamentalStatementItemFactor, "free_cash_flow_ttm")
    assert value(service, ttm, share, T) == pytest.approx(sum(cash_flow(q)["freeCashFlow"] for q in range(7, 11)))
    yoy = calc(p, CompanyShareFundamentalGrowthFactor, "revenue_growth_yoy")
    assert value(service, yoy, share, T) == pytest.approx(income(10)["revenue"] / income(6)["revenue"] - 1)
    roe = calc(p, CompanyShareFundamentalProfitabilityFactor, "roe")
    equity = (balance(9)["totalStockholdersEquity"] + balance(10)["totalStockholdersEquity"]) / 2
    assert value(service, roe, share, T) == pytest.approx(income(10)["netIncome"] / equity)


# -- source selection: one provider per value, FMP first, Eulerpool when FMP has nothing --

def test_fmp_first_when_both_serve_the_share():
    p, share, service, session, fmp_session = make_world(eulerpool=True, fmp_symbols=(fake_fmp.SYMBOL,))
    margin = calc(p, CompanyShareFundamentalProfitabilityFactor, "gross_margin")
    assert value(service, margin, share, T) == pytest.approx(income(10)["grossProfit"] / income(10)["revenue"])
    assert lineage_sources(p, margin, share, T)[0] == {"fmp"}
    assert fmp_session.calls and not session.calls          # Eulerpool not asked at all
    p.close()


def test_eulerpool_when_fmp_does_not_cover_the_share():
    p, share, service, session, fmp_session = make_world(eulerpool=True, fmp_symbols=())      # FMP: 402
    margin = calc(p, CompanyShareFundamentalProfitabilityFactor, "gross_margin")
    assert value(service, margin, share, T) == pytest.approx(income(10)["grossProfit"] / income(10)["revenue"])
    assert lineage_sources(p, margin, share, T)[0] == {"eulerpool"}
    assert fmp_session.calls and session.calls
    p.close()


def test_no_statement_provider_enabled_means_no_value_and_no_request():
    p, share, service, session, _ = make_world(eulerpool=False)
    margin = calc(p, CompanyShareFundamentalProfitabilityFactor, "gross_margin")
    assert value(service, margin, share, T) is None and session.calls == []
    p.close()


# -- three sources, one pipeline --

def test_ibkr_fmp_and_eulerpool_through_the_same_pipeline():
    """The valuation factor reads an IBKR close and the statements: with Eulerpool statements, with FMP statements -
    the same factor class, the same resolver, the same FactorValue store."""
    expected_eps = sum(income(q)["epsDiluted"] for q in range(4, 8))            # fiscal 2024, public at T
    for fmp_symbols, eulerpool, source in ((None, True, "eulerpool"), ((fake_fmp.SYMBOL,), False, "fmp")):
        p, share, service, _, _ = make_world(eulerpool=eulerpool, fmp_symbols=fmp_symbols)
        close = p.factory.get_local_repository("CompanyShareFactor")._create_or_get(
            CompanyShareFactor, "close", group="price", subgroup="TRADES", frequency="1d", source="ibkr")
        p.factory.get_local_repository("FactorValue").add_bulk(
            [FactorValue(id=None, factor_id=close.id, entity=None, entity_id=share.id, entity_type="CompanyShare",
                         date=datetime(2025, 12, 30), value="50.0")])
        ey = calc(p, CompanyShareFundamentalValuationFactor, "earnings_yield", frequency="1y")
        # XBRL per-share values come with 4 decimals
        assert value(service, ey, share, T) == pytest.approx(expected_eps / 50.0, rel=1e-4), source
        assert lineage_sources(p, ey, share, T)[0] == {"ibkr", source}
        p.close()
    assert issubclass(IBKRFactorValueRepository, FactorValueProviderPort)
