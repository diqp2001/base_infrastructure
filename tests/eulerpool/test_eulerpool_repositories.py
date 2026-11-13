"""Eulerpool repositories: the eight Fundamentals endpoints, and the statements in canonical point-in-time form
(fake Eulerpool, nothing downloaded)."""

from datetime import date, datetime, timedelta

import pytest

from src.domain.ports.factor.financial_statement_source_port import FinancialStatementSourcePort
from src.infrastructure.repositories.eulerpool_repo.eulerpool_client import EulerpoolClient, EulerpoolNotFound
from src.infrastructure.repositories.eulerpool_repo.fundamentals.eulerpool_financial_statement_repository import (
    STATEMENT_REPOSITORIES,
    EulerpoolBalanceSheetRepository,
    EulerpoolCashFlowStatementRepository,
    EulerpoolIncomeStatementRepository,
)
from src.infrastructure.repositories.eulerpool_repo.fundamentals.eulerpool_fundamentals_repository import (
    EulerpoolFundamentalsRepository,
)
from tests.eulerpool import fake_eulerpool as fake
from tests.eulerpool.fake_eulerpool import KEY, FakeSession, filed, original_filed
from tests.fmp.fake_fmp import QUARTER_ENDS, balance, cash_flow, income


def client(session=None):
    return EulerpoolClient(KEY, session=session or FakeSession(), min_interval=0, sleep=lambda s: None)


@pytest.fixture
def fundamentals():
    session = FakeSession()
    return EulerpoolFundamentalsRepository(client(session)), session


def midnight(d: date) -> datetime:
    return datetime.combine(d, datetime.min.time())


def public(i: int) -> datetime:
    """Expected availability of quarter i: the earlier of the filing date shown + 1 day and the SEC deadline bound."""
    deadline = 105 if i % 4 == 3 else 50
    return min(midnight(filed(i) + timedelta(days=1)), midnight(QUARTER_ENDS[i] + timedelta(days=deadline + 1)))


# -- the eight endpoints --

def test_statement_endpoints_return_facts_with_their_filing(fundamentals):
    repo, session = fundamentals
    facts = repo.get_income_statement("acme", fiscal_period="q1")
    url, params, _ = session.calls[-1]
    assert url.endswith("/fundamentals/financials/ACME/income-statement") and params == {"fiscal_period": "Q1"}
    revenue = [f for f in facts if f.tag == "Revenues"]
    assert [f.period_end for f in revenue] == [QUARTER_ENDS[0], QUARTER_ENDS[4], QUARTER_ENDS[8]]
    first = revenue[0]
    assert (first.value, first.unit, first.form, first.filed, first.cik) == (
        income(0)["revenue"], "USD", "10-Q", filed(0), "1")
    assert {f.tag for f in repo.get_balance_sheet("ACME", form="10-K")} >= {"Assets", "StockholdersEquity"}
    assert session.calls[-1][1] == {"form": "10-K"}
    assert {f.tag for f in repo.get_cash_flow("ACME")} == set(fake.CF_TAGS.values())
    with pytest.raises(ValueError):
        repo.get_income_statement("ACME", fiscal_period="H1")


def test_xbrl_facts_search_ratios_company_and_annual_report(fundamentals):
    repo, session = fundamentals
    facts = repo.get_financial_facts("ACME", tag="Assets", limit=5000)
    assert session.calls[-1][1] == {"tag": "Assets", "limit": 2000}
    assert facts and all(f.tag == "Assets" and f.filed is None for f in facts)        # no filing date there
    found = repo.search_xbrl_facts("Revenues", limit=1000)
    assert session.calls[-1][1] == {"tag": "Revenues", "limit": 500} and found[0].ticker == "ACME"
    with pytest.raises(ValueError):
        repo.search_xbrl_facts(" ")
    ratios = repo.get_financial_ratios("ACME")
    assert ratios.fiscal_year == 2025 and ratios.ratios == {"pe_ratio": None, "pb_ratio": None,
                                                            "debt_to_equity": 0.5, "roe": 12.5, "profit_margin": 15.0}
    info = repo.get_company_info("ACME")
    assert (info.cik, info.company_name, info.sic, info.fiscal_year_end) == ("1", "Acme Corp", "3571", "1231")
    report = repo.get_annual_report("ACME", year=2025)
    assert session.calls[-1][1] == {"year": 2025} and report.report == {"items": ["1", "7"]}
    with pytest.raises(EulerpoolNotFound):
        repo.get_company_info("NOPE")


def test_rows_without_a_number_or_a_date_are_dropped():
    assert EulerpoolFundamentalsRepository.fact({"tag": "Revenues", "val": None, "period_end": "2025-01-01"}) is None
    assert EulerpoolFundamentalsRepository.fact({"tag": "Revenues", "val": "1", "period_end": None}) is None
    assert EulerpoolFundamentalsRepository.fact({"tag": "", "val": "1", "period_end": "2025-01-01"}) is None
    fact = EulerpoolFundamentalsRepository.fact({"tag": "Revenues", "val": "12.5000", "period_end": "2025-03-31T00:00:00.000Z"})
    assert fact.value == 12.5 and fact.period_end == date(2025, 3, 31)


# -- statements in canonical form --

def records(cls, frequency, session=None):
    return cls(client(session)).fetch(fake.SYMBOL, frequency)


def test_all_three_statements_are_statement_sources():
    assert all(issubclass(cls, FinancialStatementSourcePort) for cls in STATEMENT_REPOSITORIES.values())
    assert set(STATEMENT_REPOSITORIES) == {"income_statement", "balance_sheet", "cash_flow"}


def test_income_statement_quarters_and_the_derived_fourth_quarter():
    rows = records(EulerpoolIncomeStatementRepository, "1q")
    assert [r.period_end for r in rows] == QUARTER_ENDS                   # 12 quarters, Q4 derived from the 10-K
    for i, r in enumerate(rows):
        assert r.period == f"Q{i % 4 + 1}" and r.fiscal_year == QUARTER_ENDS[i].year
        assert r.values["revenue"] == pytest.approx(income(i)["revenue"])
        assert r.values["netIncome"] == pytest.approx(income(i)["netIncome"])
        assert r.values["grossProfit"] == pytest.approx(income(i)["grossProfit"])
        assert r.reported_currency == "USD" and r.cik == "0000000001" and r.accepted_at is None
    assert "eps" in rows[2].values and "eps" not in rows[3].values         # per-share values are not derived for Q4
    assert rows[1].values["revenue"] != 1.0                                  # the 8-K figure is never used


def test_cash_flow_year_to_date_becomes_quarters_with_canonical_signs():
    rows = records(EulerpoolCashFlowStatementRepository, "1q")
    assert [r.period_end for r in rows] == QUARTER_ENDS
    for i, r in enumerate(rows):
        assert r.values["operatingCashFlow"] == pytest.approx(cash_flow(i)["operatingCashFlow"])
        assert r.values["capitalExpenditure"] == pytest.approx(cash_flow(i)["capitalExpenditure"])
        assert r.values["capitalExpenditure"] < 0


def test_balance_sheet_quarters_and_the_year_end_as_fourth_quarter():
    rows = records(EulerpoolBalanceSheetRepository, "1q")
    assert [r.period_end for r in rows] == QUARTER_ENDS
    for i, r in enumerate(rows):
        assert r.values["totalAssets"] == balance(i)["totalAssets"]          # never the 10-Q's year-end comparative
        assert r.values["totalStockholdersEquity"] == balance(i)["totalStockholdersEquity"]


def test_annual_statements_drop_the_quarter_tagged_as_fy():
    rows = records(EulerpoolIncomeStatementRepository, "1y")
    assert [(r.period, r.period_end) for r in rows] == [("FY", QUARTER_ENDS[i]) for i in (3, 7, 11)]
    assert rows[0].values["revenue"] == pytest.approx(sum(income(q)["revenue"] for q in range(4)))
    years = records(EulerpoolCashFlowStatementRepository, "1y")
    assert years[-1].values["capitalExpenditure"] == pytest.approx(sum(cash_flow(q)["capitalExpenditure"]
                                                                       for q in range(8, 12)))


def test_availability_is_capped_by_the_sec_deadline_never_before_the_filing():
    rows = records(EulerpoolIncomeStatementRepository, "1q")
    for i, r in enumerate(rows):
        expected = public(i)
        if i % 4 == 3:          # derived Q4: public when its last component is (the 10-K)
            expected = max(public(i), public(i - 1))
        assert r.available_at == expected, i
        assert r.available_at >= midnight(original_filed(i) + timedelta(days=1))      # never before the real filing
        assert r.available_at > midnight(r.period_end)
    # an old period: the comparative a year later would be too late, the deadline bound applies (10-Q: 50 days + 1)
    assert rows[0].available_at == midnight(QUARTER_ENDS[0] + timedelta(days=51))
    # the latest periods carry their original filing
    assert rows[10].available_at == midnight(original_filed(10) + timedelta(days=1))


def test_a_fourth_quarter_tagged_fy_rebuilds_the_year():
    """A 10-K row at the year end that is in fact the fourth quarter (revenue below Q1 + Q2 + Q3)."""
    def rows(statement, fiscal_period=None):
        out = fake.statement_rows(statement, fiscal_period)
        for r in out:
            if r["form"] == "10-K" and r["period_end"] == QUARTER_ENDS[7].isoformat() and r["tag"] == "Revenues":
                r["val"] = f"{income(7)['revenue']:.4f}"
            if r["form"] == "10-K" and r["period_end"] == QUARTER_ENDS[7].isoformat() and r["tag"] == "NetIncomeLoss":
                r["val"] = f"{income(7)['netIncome']:.4f}"
        return out
    session = FakeSession(statements=rows)
    repo = EulerpoolIncomeStatementRepository(client(session))
    quarters = {r.period_end: r for r in repo.fetch(fake.SYMBOL, "1q")}
    years = {r.period_end: r for r in repo.fetch(fake.SYMBOL, "1y")}
    assert quarters[QUARTER_ENDS[7]].values["revenue"] == income(7)["revenue"]
    assert years[QUARTER_ENDS[7]].values["revenue"] == pytest.approx(sum(income(q)["revenue"] for q in range(4, 8)))
    assert years[QUARTER_ENDS[7]].values["netIncome"] == pytest.approx(sum(income(q)["netIncome"] for q in range(4, 8)))


def test_requests_one_per_period_type_cached_across_frequencies():
    session = FakeSession()
    repo = EulerpoolIncomeStatementRepository(client(session))
    repo.fetch(fake.SYMBOL, "1q")
    repo.fetch(fake.SYMBOL, "1y")
    assert sorted(c[1]["fiscal_period"] for c in session.calls) == ["FY", "Q1", "Q2", "Q3"]
    with pytest.raises(ValueError):
        repo.fetch(fake.SYMBOL, "1d")


def test_an_unknown_security_raises_and_an_empty_answer_gives_no_record():
    with pytest.raises(EulerpoolNotFound):
        records(EulerpoolIncomeStatementRepository, "1q", FakeSession(symbols=()))
    empty = FakeSession(statements=lambda statement, fiscal_period=None: [])
    assert records(EulerpoolIncomeStatementRepository, "1q", empty) == []
