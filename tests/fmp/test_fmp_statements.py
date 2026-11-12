"""FMP statement repositories: requests per fiscal period, normalization of the filing's data and fields, duplicates
and rows that cannot be placed in time (fake FMP - nothing is downloaded)."""

from datetime import date, datetime

import pytest

from src.infrastructure.repositories.fmp_repo.finance.financial_statements.fmp_financial_statement_repository import (
    FMPBalanceSheetRepository, FMPCashFlowStatementRepository, FMPIncomeStatementRepository, StatementRecord,
)
from src.infrastructure.repositories.fmp_repo.fmp_client import FMPClient, FMPSubscriptionError
from tests.fmp.fake_fmp import FakeSession, accepted, row

RAW = {"date": "2025-09-27", "symbol": "AAPL", "reportedCurrency": "USD", "cik": "0000320193",
       "filingDate": "2025-10-31", "acceptedDate": "2025-10-31 06:01:26", "fiscalYear": "2025", "period": "Q4",
       "revenue": 102466000000, "netIncome": "27466000000", "eps": None, "grossProfit": "n/a"}


def repo(cls=FMPIncomeStatementRepository, session=None):
    session = session or FakeSession()
    return cls(FMPClient("k", session=session, min_interval=0), limit=5), session


def test_quarters_are_asked_one_fiscal_quarter_at_a_time_and_years_as_fy():
    r, session = repo()
    quarters = r.fetch("acme", "1q")
    assert [c[1]["period"] for c in session.calls] == ["Q1", "Q2", "Q3", "Q4"]
    assert all(c[1]["symbol"] == "ACME" and c[1]["limit"] == 5 for c in session.calls)
    assert len(quarters) == 12 and [q.period for q in quarters[:4]] == ["Q1", "Q2", "Q3", "Q4"]
    assert [q.available_at for q in quarters] == sorted(q.available_at for q in quarters)   # oldest publication first
    years = r.fetch("ACME", "1y")
    assert session.calls[-1][1]["period"] == "FY" and [y.fiscal_year for y in years] == [2023, 2024, 2025]
    with pytest.raises(ValueError):
        r.fetch("ACME", "1d")


def test_a_row_keeps_the_filings_data_and_its_fields_as_numbers():
    r, _ = repo()
    rec = r.normalize(RAW, "1q", "AAPL")
    assert (rec.period, rec.fiscal_year, rec.period_end, rec.filing_date) == ("Q4", 2025, date(2025, 9, 27),
                                                                               date(2025, 10, 31))
    assert rec.accepted_at == datetime(2025, 10, 31, 6, 1, 26) == rec.available_at       # public at acceptance
    assert (rec.reported_currency, rec.cik, rec.statement, rec.frequency) == ("USD", "0000320193", "income_statement", "1q")
    assert rec.values["revenue"] == 102466000000.0 and rec.values["netIncome"] == 27466000000.0
    assert rec.values["eps"] is None and rec.values["grossProfit"] is None and rec.values["ebitda"] is None
    assert rec.metadata() == {"date": "2025-09-27", "filingDate": "2025-10-31", "acceptedDate": "2025-10-31 06:01:26",
                              "fiscalYear": "2025", "period": "Q4", "reportedCurrency": "USD", "cik": "0000320193"}


def test_without_an_acceptance_time_a_filing_is_public_the_day_after_its_filing_date_and_without_both_it_is_dropped():
    r, _ = repo()
    rec = r.normalize({**RAW, "acceptedDate": None}, "1q", "AAPL")
    assert rec.available_at == datetime(2025, 11, 1)
    assert r.normalize({**RAW, "acceptedDate": None, "filingDate": None}, "1q", "AAPL") is None


@pytest.mark.parametrize("change", [{"period": "FY"}, {"date": None}, {"date": "27/09/2025"}, {"symbol": "MSFT"}])
def test_a_row_that_is_not_this_symbols_statement_at_this_frequency_is_dropped(change):
    r, _ = repo()
    assert r.normalize({**RAW, **change}, "1q", "AAPL") is None
    assert r.normalize({**RAW, "period": "Q2"}, "1y", "AAPL") is None


def test_one_record_per_period_and_per_publication_moment():
    first = FMPIncomeStatementRepository.deduplicate
    a = StatementRecord("X", "income_statement", "1q", "Q1", 2025, date(2025, 3, 31), date(2025, 5, 1),
                        datetime(2025, 5, 1, 16), "USD", None, {"revenue": 1.0})
    amended = StatementRecord("X", "income_statement", "1q", "Q1", 2025, date(2025, 3, 31), date(2025, 6, 1),
                              datetime(2025, 6, 1, 16), "USD", None, {"revenue": 2.0})
    assert first([amended, a]) == [a]                                  # the first published version of a period
    late = StatementRecord("X", "income_statement", "1q", "Q2", 2025, date(2025, 6, 30), date(2025, 5, 1),
                           datetime(2025, 5, 1, 16), "USD", None, {"revenue": 3.0})
    assert first([a, late]) == [late]                                  # two periods at one moment: the later one


def test_the_three_statements_and_a_symbol_outside_the_subscription():
    for cls, field in ((FMPBalanceSheetRepository, "totalDebt"), (FMPCashFlowStatementRepository, "freeCashFlow")):
        r, session = repo(cls)
        recs = r.fetch("ACME", "1q")
        assert session.calls[0][0].endswith(cls.ENDPOINT) and recs[-1].values[field] is not None
        assert recs[-1].available_at == accepted(11)
    r, _ = repo()
    with pytest.raises(FMPSubscriptionError):
        r.fetch("ZZZZ", "1y")


def test_an_annual_row_carries_the_years_flows_and_the_year_end_stocks():
    assert row("income-statement", 7, "FY")["revenue"] == sum(1000.0 + 50 * i for i in range(4, 8))
    assert row("balance-sheet-statement", 7, "FY")["totalAssets"] == 5000.0 + 700
