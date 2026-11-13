"""FMP in the SAME FactorValue pipeline as IBKR (in-memory SQLite, fake FMP - nothing is downloaded):

    FMP /stable -> fmp_repo (FMPClient, statement repositories, StatementRecord) -> FMPFactorValueRepository
    (FactorValueProviderPort, reached by FactorValueResolutionService through RepositoryFactory.factor_value_provider)
    -> raw CompanyShareFactor series -> dependencies (DependencySpec) -> calculate() -> FactorValueRepository

The resolver names no provider: a provider family is a FactorValueProviderPort the factory returns for it."""

from datetime import timedelta

import pytest

from src.application.services.data.entities.factor.factor_value_resolution_service import (
    FactorValueResolutionService,
)
from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.observation_quality import ObservationRef
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_profitability_factor import (
    CompanyShareFundamentalProfitabilityFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_statement_item_factor import (
    CompanyShareFundamentalStatementItemFactor,
)
from src.domain.ports.factor.factor_value_provider_port import FactorValueProviderPort
from src.infrastructure.models.factor.factor_value import FactorValueModel
from src.infrastructure.repositories.fmp_repo.factor.fmp_factor_value_repository import FMPFactorValueRepository
from src.infrastructure.repositories.fmp_repo.fmp_client import FMPClient
from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository
from tests.fmp import fake_fmp
from tests.fmp.fake_fmp import FakeSession, accepted, balance, cash_flow, income
from tests.fmp.test_fmp_fundamental_pipeline import T, calc, raw, value
from tests.misbuffet.sqlite_portfolio import SqlitePortfolio

# the representative primitives: (statement, FMP field, expected at T = the quarter published last, index 10)
PRIMITIVES = [
    ("income_statement", "revenue", income(10)["revenue"]),
    ("income_statement", "netIncome", income(10)["netIncome"]),
    ("income_statement", "ebitda", income(10)["ebitda"]),
    ("income_statement", "eps", income(10)["eps"]),
    ("balance_sheet", "totalAssets", balance(10)["totalAssets"]),
    ("balance_sheet", "totalDebt", balance(10)["totalDebt"]),
    ("balance_sheet", "totalEquity", balance(10)["totalEquity"]),
    ("balance_sheet", "netDebt", balance(10)["netDebt"]),
    ("cash_flow", "operatingCashFlow", cash_flow(10)["operatingCashFlow"]),
    ("cash_flow", "capitalExpenditure", cash_flow(10)["capitalExpenditure"]),
    ("cash_flow", "freeCashFlow", cash_flow(10)["freeCashFlow"]),
]


@pytest.fixture
def world():
    p = SqlitePortfolio(cash=0.0, shares=(fake_fmp.SYMBOL,))
    session = FakeSession()
    p.factory.create_fmp_repositories(FMPClient("test-key", session=session, min_interval=0))
    share = p.factory.get_local_repository("CompanyShare").get_by_symbol(fake_fmp.SYMBOL)
    yield p, share, FactorValueResolutionService(factory=p.factory), session
    p.close()


def stored(p, factor, share):
    return (p.session.query(FactorValueModel)
            .filter_by(factor_id=factor.id, entity_id=share.id, entity_type="CompanyShare")
            .order_by(FactorValueModel.date).all())


@pytest.mark.parametrize("statement, field, expected", PRIMITIVES, ids=[f for _, f, _ in PRIMITIVES])
def test_each_representative_primitive_reaches_the_factor_value_store(world, statement, field, expected):
    p, share, service, _ = world
    factor = raw(p, field, statement)
    fv = service.resolve_factor_value(factor, share, T)
    assert float(fv.value) == expected
    rows = stored(p, factor, share)
    # the whole published history, each value at its publication (never at the period's end)
    assert [r.date.replace(tzinfo=None) for r in rows] == [accepted(i) for i in range(12)]
    assert fv.date.replace(tzinfo=None) == accepted(10)
    assert (factor.source, factor.group, factor.subgroup, factor.frequency) == ("fmp", "fundamental", statement, "1q")


def test_the_filings_data_travel_with_the_values(world):
    p, share, service, _ = world
    service.resolve_factor_value(raw(p, "revenue"), share, T)
    at = accepted(10)
    filing = {name: next(r.value for r in stored(p, raw(p, name), share) if r.date.replace(tzinfo=None) == at)
              for name in ("date", "filingDate", "acceptedDate", "fiscalYear", "period", "reportedCurrency", "cik")}
    assert filing == {"date": "2025-09-30", "filingDate": at.date().isoformat(),
                      "acceptedDate": at.strftime("%Y-%m-%d %H:%M:%S"), "fiscalYear": "2025", "period": "Q3",
                      "reportedCurrency": "USD", "cik": "0000000001"}
    usd = p.factory.get_local_repository("Currency").get_by_iso_code("USD")
    if usd is not None:          # amounts carry the reported currency
        assert {r.currency_id for r in stored(p, raw(p, "revenue"), share)} == {usd.id}


def test_free_cash_flow_from_its_components_through_the_dependencies(world):
    p, share, service, _ = world
    fcf = calc(p, CompanyShareFundamentalStatementItemFactor, "free_cash_flow")
    fv = service.resolve_factor_value(fcf, share, T)
    expected = cash_flow(10)["operatingCashFlow"] + cash_flow(10)["capitalExpenditure"]
    assert float(fv.value) == expected == cash_flow(10)["freeCashFlow"]        # = FMP's own total
    assert [r.date.replace(tzinfo=None) for r in stored(p, fcf, share)] == [T]
    # lineage: the two raw FMP values it was computed from, as published
    lineage = p.factory.observation_provenance_local_repo.get(ObservationRef(fcf.id, "CompanyShare", share.id, T))
    inputs = {(ref.factor_id, ref.observed_at) for ref in lineage.inputs}
    assert inputs == {(raw(p, "operatingCashFlow", "cash_flow").id, accepted(10)),
                      (raw(p, "capitalExpenditure", "cash_flow").id, accepted(10))}
    # the raw provider total stays a separate series (source fmp), the calculated one is source 'calculated'
    assert fcf.source == "calculated" and raw(p, "freeCashFlow", "cash_flow").source == "fmp"
    ttm = calc(p, CompanyShareFundamentalStatementItemFactor, "free_cash_flow_ttm")
    assert value(service, ttm, share, T) == sum(cash_flow(q)["freeCashFlow"] for q in range(7, 11))
    net_debt = calc(p, CompanyShareFundamentalStatementItemFactor, "net_debt")
    assert value(service, net_debt, share, T) == balance(10)["totalDebt"] - balance(10)["cashAndCashEquivalents"]


def test_gross_margin_through_revenue_and_gross_profit(world):
    p, share, service, _ = world
    margin = calc(p, CompanyShareFundamentalProfitabilityFactor, "gross_margin")
    assert value(service, margin, share, T) == pytest.approx(income(10)["grossProfit"] / income(10)["revenue"])
    lineage = p.factory.observation_provenance_local_repo.get(ObservationRef(margin.id, "CompanyShare", share.id, T))
    assert {ref.factor_id for ref in lineage.inputs} == {raw(p, "revenue").id, raw(p, "grossProfit").id}
    # before the quarter was published the margin is the previous quarter's: no look-ahead
    before = accepted(10) - timedelta(seconds=1)
    assert value(service, margin, share, before) == pytest.approx(income(9)["grossProfit"] / income(9)["revenue"])


def test_both_providers_implement_the_one_provider_port(world):
    p, _, _, _ = world
    assert issubclass(IBKRFactorValueRepository, FactorValueProviderPort)
    assert isinstance(p.factory.factor_value_provider("fmp"), FMPFactorValueRepository)
    assert p.factory.factor_value_provider("unknown") is None
    assert p.factory.provider_family_enabled("fmp", "fmp") is True
    assert p.factory.provider_family_enabled("ibkr", "ibkr") is True                  # IBKR: on demand, as before
    fresh = SqlitePortfolio(cash=0.0, shares=("X",))
    assert fresh.factory.provider_family_enabled("fmp", "fmp") is False                # FMP: only once enabled
    assert fresh.factory.factor_value_provider("fmp") is None
    fresh.close()


def test_the_resolver_reaches_any_provider_family_through_the_port(world):
    """A provider family the resolver has never heard of: no change in the application layer."""
    p, share, service, _ = world

    class StandIn(FactorValueProviderPort):
        def __init__(self):
            self.asked = []

        def fetch_factor_value(self, factor_entity, entity, time_date, **kwargs):
            self.asked.append((factor_entity.name, entity.id, time_date))
            fv = FactorValue(id=None, factor_id=factor_entity.id, entity=None, entity_id=entity.id,
                             entity_type="CompanyShare", date=time_date, value="42.0")
            p.factory.get_local_repository("FactorValue").add_bulk([fv])
            return fv

    stand_in = StandIn()
    p.factory._available_repository_families["stand_in"] = True
    original = p.factory.factor_value_provider
    p.factory.factor_value_provider = lambda family: stand_in if family == "stand_in" else original(family)
    factor = p.factory.get_local_repository("CompanyShareFactor")._create_or_get(
        type(raw(p, "revenue")), "custom", group="price", subgroup="TRADES", frequency="1d", source="calculated")
    assert value(service, factor, share, T) == 42.0 and stand_in.asked == [("custom", share.id, T)]
