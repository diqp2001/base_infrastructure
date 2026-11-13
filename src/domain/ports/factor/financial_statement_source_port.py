"""
FinancialStatementSourcePort - a data provider's company financial statements in the project's canonical form.

Every provider (FMP, Eulerpool, ...) maps its own response (FMP fields, SEC XBRL tags, ...) into StatementRecord:
one statement of one fiscal period, with the canonical field names of
CompanyShareFundamentalFactor.STATEMENT_FIELDS and the moment the figures became public (``available_at``). The
generic StatementFactorValueRepository turns those records into raw factor values; the factors never see a
provider's field names.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class StatementRecord:
    """One statement of one fiscal period, as filed (canonical field names)."""
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
    # an upper bound on the publication set by the provider when its filing date is not the original one
    # (e.g. Eulerpool keeps the latest filing that repeated a period): the record is public at the earlier of the two
    available_by: Optional[datetime] = None

    @property
    def available_at(self) -> Optional[datetime]:
        """When the figures became public: the acceptance time, else the day after the filing date; never later
        than ``available_by`` when the provider sets one."""
        if self.accepted_at is not None:
            stamp = self.accepted_at
        elif self.filing_date is not None:
            stamp = datetime.combine(self.filing_date + timedelta(days=1), datetime.min.time())
        else:
            stamp = None
        if self.available_by is not None:
            return self.available_by if stamp is None else min(stamp, self.available_by)
        return stamp

    def metadata(self) -> Dict[str, Optional[str]]:
        """The filing's data as stored (series names: CompanyShareFundamentalFactor.METADATA_FIELDS)."""
        return {
            "date": self.period_end.isoformat(),
            "filingDate": self.filing_date.isoformat() if self.filing_date else None,
            "acceptedDate": self.accepted_at.isoformat(sep=" ") if self.accepted_at else None,
            "fiscalYear": str(self.fiscal_year) if self.fiscal_year is not None else None,
            "period": self.period,
            "reportedCurrency": self.reported_currency,
            "cik": self.cik,
        }


class FinancialStatementSourcePort(ABC):
    """One statement (STATEMENT) of a provider, at the frequencies it serves (FREQUENCIES)."""

    STATEMENT: str = ""
    FREQUENCIES: Tuple[str, ...] = ()

    @abstractmethod
    def fetch(self, symbol: str, frequency: str) -> List[StatementRecord]:
        """Every period of the statement at that frequency, oldest publication first (the whole history the
        provider serves, never only the latest). Raises the provider's error on a failed request."""
