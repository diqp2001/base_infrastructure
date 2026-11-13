"""
Eulerpool Fundamentals API (/fundamentals/...) - the eight endpoints, normalized (checked live 2026-11-13):

    get_income_statement / get_balance_sheet / get_cash_flow   /financials/{id}/income-statement | balance-sheet |
                                                               cash-flow  (fiscal_period FY|Q1..Q4, form 10-K|10-Q)
    get_financial_facts                                        /financials/{id}  (tag, fiscal_period, form, limit<=2000)
    get_financial_ratios                                       /financials/{id}/ratios  (latest fiscal year only)
    get_company_info                                           /company/{id}
    get_annual_report                                          /annual-report/{id}  (year)
    search_xbrl_facts                                          /facts/search  (tag required, fiscal_period, form,
                                                               min_val, limit<=500; latest value per company)

Statement and fact rows are SEC XBRL facts, one per (tag, period end, form): XBRLFact. ``fiscal_year`` /
``fiscal_period`` / ``form`` / ``filed`` are those of the FILING the value was taken from - for a period older than
the latest, Eulerpool keeps the LATEST filing that repeated it (a later year's comparative), not the original one.
No period start is given (a 10-Q cash flow is year-to-date, an income statement value the quarter). The facts and
search endpoints have no filing date at all. Turning facts into point-in-time statements is
eulerpool_financial_statement_repository's job; ratios, company info and the annual report are reference / document
data, never factor values here (no history, no publication date).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

from src.infrastructure.repositories.eulerpool_repo.base_eulerpool_repository import BaseEulerpoolRepository
from src.infrastructure.repositories.eulerpool_repo.eulerpool_client import EulerpoolResponseError, identifier_path
from src.infrastructure.repositories.fundamental_provider.statement_records import number, parse_date

logger = logging.getLogger(__name__)

STATEMENT_ENDPOINTS = {"income_statement": "income-statement", "balance_sheet": "balance-sheet",
                       "cash_flow": "cash-flow"}
FISCAL_PERIODS = ("FY", "Q1", "Q2", "Q3", "Q4")
ROW_CAP = 1000                      # the statement endpoints answer at most 1000 rows (no paging)


@dataclass(frozen=True)
class XBRLFact:
    """One SEC XBRL fact as Eulerpool serves it (fiscal_year / fiscal_period / form / filed: of the filing)."""
    tag: str
    value: float
    unit: Optional[str]
    period_end: date
    fiscal_year: Optional[int]
    fiscal_period: Optional[str]
    form: Optional[str]
    filed: Optional[date]
    taxonomy: Optional[str] = None
    cik: Optional[str] = None
    ticker: Optional[str] = None


@dataclass(frozen=True)
class FinancialRatios:
    """The latest fiscal year's ratios (no history: not a point-in-time series)."""
    ticker: Optional[str]
    fiscal_year: Optional[int]
    ratios: Dict[str, Optional[float]] = field(default_factory=dict)


@dataclass(frozen=True)
class CompanyInfo:
    """SEC company data (reference data, not a factor)."""
    cik: Optional[str]
    ticker: Optional[str]
    company_name: Optional[str]
    sic: Optional[str]
    sic_description: Optional[str]
    state: Optional[str]
    fiscal_year_end: Optional[str]          # MMDD


@dataclass(frozen=True)
class AnnualReport:
    """A 10-K as JSON: document data, kept raw (never turned into factor values)."""
    ticker: Optional[str]
    as_of: Optional[str]
    updated_at: Optional[str]
    report: Any


def _int(value) -> Optional[int]:
    v = number(value)
    return int(v) if v is not None else None


def _text(value) -> Optional[str]:
    return str(value).strip() or None if value is not None else None


class EulerpoolFundamentalsRepository(BaseEulerpoolRepository):
    """Raw access to the Eulerpool Fundamentals API (one request per call, answers normalized, nothing stored)."""

    # -- normalization --
    @staticmethod
    def fact(row: Dict[str, Any]) -> Optional[XBRLFact]:
        """An XBRLFact, or None for a row without a tag, a number or a period end."""
        if not isinstance(row, dict):
            return None
        value, period_end, tag = number(row.get("val")), parse_date(row.get("period_end")), _text(row.get("tag"))
        if value is None or period_end is None or not tag:
            return None
        return XBRLFact(tag=tag, value=value, unit=_text(row.get("unit")), period_end=period_end,
                        fiscal_year=_int(row.get("fiscal_year")), fiscal_period=_text(row.get("fiscal_period")),
                        form=_text(row.get("form")), filed=parse_date(row.get("filed")),
                        taxonomy=_text(row.get("taxonomy")), cik=_text(row.get("cik")), ticker=_text(row.get("ticker")))

    def _facts(self, path: str, **params) -> List[XBRLFact]:
        data = self.eulerpool_client.get(path, **params)
        if not isinstance(data, list):
            raise EulerpoolResponseError(f"{path}: expected a list of facts, got {type(data).__name__}")
        facts = [f for f in (self.fact(row) for row in data) if f is not None]
        if len(data) - len(facts):
            logger.info(f"Eulerpool {path}: {len(data) - len(facts)} rows without tag / value / period end dropped")
        if len(data) >= ROW_CAP:
            logger.warning(f"Eulerpool {path} {params}: {len(data)} rows - the answer may be truncated at {ROW_CAP}")
        return facts

    @staticmethod
    def _period(fiscal_period: Optional[str]) -> Optional[str]:
        if fiscal_period is None:
            return None
        value = str(fiscal_period).strip().upper()
        if value not in FISCAL_PERIODS:
            raise ValueError(f"fiscal_period {fiscal_period!r}: one of {FISCAL_PERIODS}")
        return value

    # -- statements (SEC XBRL facts of one statement) --
    def get_statement(self, statement: str, identifier: str, fiscal_period: Optional[str] = None,
                      form: Optional[str] = None) -> List[XBRLFact]:
        endpoint = STATEMENT_ENDPOINTS[statement]
        return self._facts(f"fundamentals/financials/{identifier_path(identifier)}/{endpoint}",
                           fiscal_period=self._period(fiscal_period), form=form)

    def get_income_statement(self, identifier: str, fiscal_period: Optional[str] = None,
                             form: Optional[str] = None) -> List[XBRLFact]:
        return self.get_statement("income_statement", identifier, fiscal_period, form)

    def get_balance_sheet(self, identifier: str, fiscal_period: Optional[str] = None,
                          form: Optional[str] = None) -> List[XBRLFact]:
        return self.get_statement("balance_sheet", identifier, fiscal_period, form)

    def get_cash_flow(self, identifier: str, fiscal_period: Optional[str] = None,
                      form: Optional[str] = None) -> List[XBRLFact]:
        return self.get_statement("cash_flow", identifier, fiscal_period, form)

    # -- every XBRL fact of a company / one tag across companies --
    def get_financial_facts(self, identifier: str, tag: Optional[str] = None, fiscal_period: Optional[str] = None,
                            form: Optional[str] = None, limit: int = 2000) -> List[XBRLFact]:
        """The company's SEC XBRL facts (no filing date: reference data, not point in time)."""
        return self._facts(f"fundamentals/financials/{identifier_path(identifier)}", tag=tag,
                           fiscal_period=self._period(fiscal_period), form=form, limit=min(int(limit), 2000))

    def search_xbrl_facts(self, tag: str, fiscal_period: Optional[str] = None, form: Optional[str] = None,
                          min_val: Optional[float] = None, limit: int = 100) -> List[XBRLFact]:
        """The latest value of one XBRL tag for every company that reports it (tag discovery / mapping checks)."""
        if not str(tag or "").strip():
            raise ValueError("search_xbrl_facts: a tag is required")
        return self._facts("fundamentals/facts/search", tag=str(tag).strip(),
                           fiscal_period=self._period(fiscal_period), form=form, min_val=min_val,
                           limit=min(int(limit), 500))

    # -- reference and document data --
    def get_financial_ratios(self, identifier: str) -> FinancialRatios:
        data = self.eulerpool_client.get(f"fundamentals/financials/{identifier_path(identifier)}/ratios")
        if not isinstance(data, dict):
            raise EulerpoolResponseError(f"ratios {identifier}: expected an object, got {type(data).__name__}")
        ratios = {k: number(v) for k, v in data.items() if k not in ("ticker", "fiscal_year")}
        return FinancialRatios(ticker=_text(data.get("ticker")), fiscal_year=_int(data.get("fiscal_year")),
                               ratios=ratios)

    def get_company_info(self, identifier: str) -> CompanyInfo:
        data = self.eulerpool_client.get(f"fundamentals/company/{identifier_path(identifier)}")
        if not isinstance(data, dict):
            raise EulerpoolResponseError(f"company {identifier}: expected an object, got {type(data).__name__}")
        return CompanyInfo(cik=_text(data.get("cik")), ticker=_text(data.get("ticker")),
                           company_name=_text(data.get("company_name")), sic=_text(data.get("sic")),
                           sic_description=_text(data.get("sic_description")), state=_text(data.get("state")),
                           fiscal_year_end=_text(data.get("fiscal_year_end")))

    def get_annual_report(self, identifier: str, year: Optional[int] = None) -> AnnualReport:
        data = self.eulerpool_client.get(f"fundamentals/annual-report/{identifier_path(identifier)}", year=year)
        if not isinstance(data, dict):
            raise EulerpoolResponseError(f"annual report {identifier}: expected an object, got {type(data).__name__}")
        return AnnualReport(ticker=_text(data.get("ticker")), as_of=_text(data.get("as_of")),
                            updated_at=_text(data.get("updated_at")), report=data.get("report"))
