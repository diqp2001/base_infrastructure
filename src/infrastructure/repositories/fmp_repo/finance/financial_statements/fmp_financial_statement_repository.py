"""
FMP financial statements (/stable/income-statement, /balance-sheet-statement, /cash-flow-statement) normalized into
StatementRecord: the filing's data (period end, filing date, acceptance time, fiscal year and period, reported
currency, CIK) and the statement's fields (CompanyShareFundamentalFactor.STATEMENT_FIELDS) as floats.

Requests: quarterly ('1q') statements are asked one fiscal quarter at a time (period=Q1..Q4) and annual ('1y') ones
with period=FY: a subscription that caps `limit` (5 on the current plan) still gets `limit` periods of each quarter,
i.e. 4 x limit quarters. The rows are the provider's latest figures for each period.

Availability: a record is public from its acceptance time (acceptedDate, US Eastern as FMP gives it); without one,
from the day after its filing date. A record with neither is dropped (it cannot be placed in time).
Duplicates: one record per fiscal period (the first published); two periods published at the same moment keep the
later period only (a value per series and moment) - both are logged.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_factor import (
    ANNUAL, BALANCE_SHEET, CASH_FLOW, INCOME_STATEMENT, QUARTERLY, STATEMENT_FIELDS,
)
from src.infrastructure.repositories.fmp_repo.base_fmp_repository import BaseFMPRepository

logger = logging.getLogger(__name__)

PERIOD_REQUESTS = {QUARTERLY: ("Q1", "Q2", "Q3", "Q4"), ANNUAL: ("FY",)}
DEFAULT_LIMIT = 5


def _number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _date(value: Any) -> Optional[date]:
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date() if value else None
    except ValueError:
        return None


def _datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value)[:19], fmt)
        except ValueError:
            continue
    return None


@dataclass(frozen=True)
class StatementRecord:
    """One statement of one fiscal period, as filed."""
    symbol: str
    statement: str                      # income_statement | balance_sheet | cash_flow
    frequency: str                      # 1q | 1y
    period: str                         # Q1..Q4 | FY
    fiscal_year: Optional[int]
    period_end: date
    filing_date: Optional[date]
    accepted_at: Optional[datetime]
    reported_currency: Optional[str]
    cik: Optional[str]
    values: Dict[str, Optional[float]] = field(default_factory=dict)

    @property
    def available_at(self) -> Optional[datetime]:
        """When the figures became public: the acceptance time, else the day after the filing date."""
        if self.accepted_at is not None:
            return self.accepted_at
        if self.filing_date is not None:
            return datetime.combine(self.filing_date + timedelta(days=1), datetime.min.time())
        return None

    def metadata(self) -> Dict[str, Optional[str]]:
        """The filing's data as stored (series names: the provider's fields - METADATA_FIELDS)."""
        return {
            "date": self.period_end.isoformat(),
            "filingDate": self.filing_date.isoformat() if self.filing_date else None,
            "acceptedDate": self.accepted_at.isoformat(sep=" ") if self.accepted_at else None,
            "fiscalYear": str(self.fiscal_year) if self.fiscal_year is not None else None,
            "period": self.period,
            "reportedCurrency": self.reported_currency,
            "cik": self.cik,
        }


class FMPFinancialStatementRepository(BaseFMPRepository):
    """Fetches and normalizes one FMP statement. Subclasses set STATEMENT and ENDPOINT."""

    STATEMENT: str = ""
    ENDPOINT: str = ""

    def __init__(self, fmp_client, factory=None, limit: int = DEFAULT_LIMIT):
        super().__init__(fmp_client, factory)
        self.limit = limit

    @property
    def fields(self):
        return STATEMENT_FIELDS[self.STATEMENT]

    def fetch(self, symbol: str, frequency: str) -> List[StatementRecord]:
        """The statements of a symbol at a frequency, oldest publication first. Raises FMPError on a failed request
        (no partial result: a quarter that failed would be a hole in the series)."""
        if frequency not in PERIOD_REQUESTS:
            raise ValueError(f"FMP statements: unknown frequency {frequency!r} (1q | 1y)")
        symbol = symbol.strip().upper()
        records = []
        for period in PERIOD_REQUESTS[frequency]:
            for row in self.fmp_client.get(self.ENDPOINT, symbol=symbol, period=period, limit=self.limit):
                record = self.normalize(row, frequency, symbol)
                if record is not None:
                    records.append(record)
        return self.deduplicate(records)

    def normalize(self, row: Dict[str, Any], frequency: str, symbol: Optional[str] = None) -> Optional[StatementRecord]:
        """A StatementRecord, or None (logged) for a row that is not this symbol's statement at this frequency or
        cannot be placed in time."""
        row_symbol = str(row.get("symbol") or "").strip().upper()
        period = str(row.get("period") or "").strip().upper()
        period_end = _date(row.get("date"))
        if symbol and row_symbol and row_symbol != symbol:
            logger.warning(f"FMP {self.ENDPOINT}: row of {row_symbol} in the answer for {symbol} - dropped")
            return None
        if period not in PERIOD_REQUESTS[frequency] or period_end is None:
            logger.warning(f"FMP {self.ENDPOINT} {symbol}: row with period {period!r} / date {row.get('date')!r} "
                           f"is not a {frequency} statement - dropped")
            return None
        fiscal_year = _number(row.get("fiscalYear") if row.get("fiscalYear") is not None else row.get("calendarYear"))
        record = StatementRecord(
            symbol=row_symbol or (symbol or ""), statement=self.STATEMENT, frequency=frequency, period=period,
            fiscal_year=int(fiscal_year) if fiscal_year is not None else None, period_end=period_end,
            filing_date=_date(row.get("filingDate")), accepted_at=_datetime(row.get("acceptedDate")),
            reported_currency=(str(row.get("reportedCurrency")).strip() or None) if row.get("reportedCurrency") else None,
            cik=str(row.get("cik")).strip() if row.get("cik") else None,
            values={f: _number(row.get(f)) for f in self.fields},
        )
        if record.available_at is None:
            logger.warning(f"FMP {self.ENDPOINT} {symbol} {period} {period_end}: no filing / acceptance date - "
                           f"dropped (it cannot be placed in time)")
            return None
        return record

    @staticmethod
    def deduplicate(records: List[StatementRecord]) -> List[StatementRecord]:
        by_period: Dict[tuple, StatementRecord] = {}
        for r in records:
            key = (r.fiscal_year, r.period, r.period_end)
            kept = by_period.get(key)
            if kept is not None:
                logger.warning(f"FMP {r.statement} {r.symbol} {r.period} {r.period_end}: duplicate period - keeping "
                               f"the first published ({min(kept.available_at, r.available_at)})")
                if r.available_at >= kept.available_at:
                    continue
            by_period[key] = r
        by_stamp: Dict[datetime, StatementRecord] = {}
        for r in by_period.values():
            kept = by_stamp.get(r.available_at)
            if kept is not None:
                later = max((kept, r), key=lambda x: x.period_end)
                logger.warning(f"FMP {r.statement} {r.symbol}: periods {kept.period_end} and {r.period_end} published "
                               f"at the same moment {r.available_at} - keeping {later.period_end}")
                r = later
            by_stamp[r.available_at] = r
        return sorted(by_stamp.values(), key=lambda x: x.available_at)


class FMPIncomeStatementRepository(FMPFinancialStatementRepository):
    STATEMENT = INCOME_STATEMENT
    ENDPOINT = "income-statement"


class FMPBalanceSheetRepository(FMPFinancialStatementRepository):
    STATEMENT = BALANCE_SHEET
    ENDPOINT = "balance-sheet-statement"


class FMPCashFlowStatementRepository(FMPFinancialStatementRepository):
    STATEMENT = CASH_FLOW
    ENDPOINT = "cash-flow-statement"


STATEMENT_REPOSITORIES = {cls.STATEMENT: cls for cls in
                          (FMPIncomeStatementRepository, FMPBalanceSheetRepository, FMPCashFlowStatementRepository)}
