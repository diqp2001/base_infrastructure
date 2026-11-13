"""
Eulerpool financial statements (SEC XBRL facts) normalized into the project's canonical StatementRecord
(FinancialStatementSourcePort): the factors never see an XBRL tag.

Mapping: TAG_MAP[statement] = {canonical field (CompanyShareFundamentalFactor.STATEMENT_FIELDS): alternatives}, an
alternative = signed tags that must ALL be reported (first complete alternative wins). Signs follow the canonical
(FMP) convention: cash paid out is negative (capex, buybacks, dividends, acquisitions), an increase of receivables /
inventories lowers the operating cash flow. Canonical fields Eulerpool does not serve (e.g. totalDebt, ebitda,
weightedAverageShsOut) are simply absent: a factor reading them has no value.

Requests: one per fiscal period type (FY, Q1, Q2, Q3) and statement, answers cached per (symbol, statement, period
type) for the session: the quarterly and the annual series of a statement cost 4 requests together.

Facts kept: forms 10-Q / 10-K (8-K press-release figures are left out), one per (tag, period end): the earliest
filed. FY facts must end on the fiscal year end (a 10-K also tags quarterly figures as FY); Q facts must not (a 10-Q
also tags the previous fiscal year end's balances). The fiscal year end is anchored on the latest 10-K's period.

Durations (no period start in the answers): an income statement 10-Q value is the QUARTER, a cash flow 10-Q value is
YEAR-TO-DATE (SEC presentation; checked live on AAPL / PNC 2026-11-13). Quarterly series:
    income statement   Q1..Q3 as filed, Q4 = FY - Q1 - Q2 - Q3 (per-share and share-count fields: not derived)
    cash flow          Q1 = YTD1, Q2 = YTD2 - YTD1, Q3 = YTD3 - YTD2, Q4 = FY - YTD3
    balance sheet      Q1..Q3 as filed, Q4 = the fiscal year end's balance (same instant)
A derived value needs every component, and is public when the last of them is. An income statement 10-K row whose
revenue is below Q1 + Q2 + Q3 is the fourth quarter (a 10-K also tags its quarterly data): the year is then rebuilt
from the four quarters.

Point in time: Eulerpool keeps, for a period older than the latest, the LATEST filing that repeated it (the next
year's comparative), so its `filed` date is up to a year late. A value is public at the earlier of (filed + 1 day)
and the SEC deadline bound ``period end + DEADLINE_DAYS + 1 day`` (10-Q: 45 days + 5 days of late-filing extension;
10-K: 90 + 15) - never before a filer that files on time did (owner's choice 2026-11-13). Remaining gap: the value is
the latest filing's, i.e. a later restatement can replace the figure first published.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_factor import (
    ANNUAL, BALANCE_SHEET, CASH_FLOW, INCOME_STATEMENT, QUARTERLY,
)
from src.domain.ports.factor.financial_statement_source_port import FinancialStatementSourcePort, StatementRecord
from src.infrastructure.repositories.eulerpool_repo.base_eulerpool_repository import BaseEulerpoolRepository
from src.infrastructure.repositories.eulerpool_repo.fundamentals.eulerpool_fundamentals_repository import (
    EulerpoolFundamentalsRepository, XBRLFact,
)
from src.infrastructure.repositories.fundamental_provider.statement_records import deduplicate

logger = logging.getLogger(__name__)

Alternative = Tuple[Tuple[int, str], ...]

TAG_MAP: Dict[str, Dict[str, Tuple[Alternative, ...]]] = {
    INCOME_STATEMENT: {
        "revenue": (((1, "Revenues"),), ((1, "RevenueFromContractWithCustomerExcludingAssessedTax"),),
                    ((1, "SalesRevenueNet"),)),
        "costOfRevenue": (((1, "CostOfRevenue"),), ((1, "CostOfGoodsAndServicesSold"),)),
        "grossProfit": (((1, "GrossProfit"),),),
        "researchAndDevelopmentExpenses": (((1, "ResearchAndDevelopmentExpense"),),),
        "sellingGeneralAndAdministrativeExpenses": (((1, "SellingGeneralAndAdministrativeExpense"),),),
        "operatingExpenses": (((1, "OperatingExpenses"),),),
        "operatingIncome": (((1, "OperatingIncomeLoss"),),),
        "interestExpense": (((1, "InterestExpense"),),),
        "incomeTaxExpense": (((1, "IncomeTaxExpenseBenefit"),),),
        # ProfitLoss (consolidated, incl. noncontrolling interests) only when the parent's NetIncomeLoss is not
        # reported (e.g. PNC's 10-Qs): an approximation by the noncontrolling interests' share - owner may remove
        "netIncome": (((1, "NetIncomeLoss"),), ((1, "ProfitLoss"),)),
        "eps": (((1, "EarningsPerShareBasic"),),),
        "epsDiluted": (((1, "EarningsPerShareDiluted"),),),
    },
    BALANCE_SHEET: {
        "cashAndCashEquivalents": (((1, "CashAndCashEquivalentsAtCarryingValue"),),),
        "shortTermInvestments": (((1, "MarketableSecuritiesCurrent"),),),
        "accountsReceivables": (((1, "AccountsReceivableNetCurrent"),),),
        "inventory": (((1, "InventoryNet"),),),
        "totalCurrentAssets": (((1, "AssetsCurrent"),),),
        "propertyPlantEquipmentNet": (((1, "PropertyPlantAndEquipmentNet"),),),
        "goodwill": (((1, "Goodwill"),),),
        "intangibleAssets": (((1, "IntangibleAssetsNetExcludingGoodwill"),),),
        "totalNonCurrentAssets": (((1, "AssetsNoncurrent"),),),
        "totalAssets": (((1, "Assets"),),),
        "accountPayables": (((1, "AccountsPayableCurrent"),),),
        "shortTermDebt": (((1, "ShortTermBorrowings"),),),
        "totalCurrentLiabilities": (((1, "LiabilitiesCurrent"),),),
        "longTermDebt": (((1, "LongTermDebtNoncurrent"),),),
        "totalNonCurrentLiabilities": (((1, "LiabilitiesNoncurrent"),),),
        "totalLiabilities": (((1, "Liabilities"),),),
        "retainedEarnings": (((1, "RetainedEarningsAccumulatedDeficit"),),),
        "totalStockholdersEquity": (((1, "StockholdersEquity"),),),
        "totalEquity": (((1, "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),),),
    },
    CASH_FLOW: {
        "netCashProvidedByOperatingActivities": (((1, "NetCashProvidedByUsedInOperatingActivities"),),),
        "operatingCashFlow": (((1, "NetCashProvidedByUsedInOperatingActivities"),),),
        "depreciationAndAmortization": (((1, "DepreciationDepletionAndAmortization"),),),
        "stockBasedCompensation": (((1, "ShareBasedCompensation"),),),
        "accountsReceivables": (((-1, "IncreaseDecreaseInAccountsReceivable"),),),
        "inventory": (((-1, "IncreaseDecreaseInInventories"),),),
        "investmentsInPropertyPlantAndEquipment": (((-1, "PaymentsToAcquirePropertyPlantAndEquipment"),),),
        "capitalExpenditure": (((-1, "PaymentsToAcquirePropertyPlantAndEquipment"),),),
        "acquisitionsNet": (((-1, "PaymentsToAcquireBusinessesNetOfCashAcquired"),),),
        "netCashProvidedByInvestingActivities": (((1, "NetCashProvidedByUsedInInvestingActivities"),),),
        "longTermNetDebtIssuance": (((1, "ProceedsFromIssuanceOfLongTermDebt"), (-1, "RepaymentsOfLongTermDebt")),),
        "commonStockRepurchased": (((-1, "PaymentsForRepurchaseOfCommonStock"),),),
        "netDividendsPaid": (((-1, "PaymentsOfDividends"),),),
        "netCashProvidedByFinancingActivities": (((1, "NetCashProvidedByUsedInFinancingActivities"),),),
    },
}

QUARTER_TYPES = ("Q1", "Q2", "Q3")
FORMS = {"10-Q": "Q", "10-K": "FY"}
DEADLINE_DAYS = {"Q": 45 + 5, "FY": 90 + 15}         # SEC deadline of the slowest filer category + NT extension
FISCAL_YEAR_END_TOLERANCE = 10                      # days: 52/53-week fiscal years end on a weekday near the anchor
NOT_DERIVED = frozenset({"eps", "epsDiluted", "weightedAverageShsOut", "weightedAverageShsOutDil"})


class _Fact:
    """One canonical field of one period: its value and when it was public (``derived``: computed from other
    values, public exactly at ``available_by`` = when the last of them was)."""
    __slots__ = ("value", "filed", "available_by", "derived")

    def __init__(self, value: float, filed: Optional[date], available_by: datetime, derived: bool = False):
        self.value, self.filed, self.available_by, self.derived = value, filed, available_by, derived

    @property
    def available_at(self) -> datetime:
        if self.derived:
            return self.available_by
        stamp = datetime.combine(self.filed + timedelta(days=1), datetime.min.time()) if self.filed else None
        return self.available_by if stamp is None else min(stamp, self.available_by)


def _midnight(d: date) -> datetime:
    return datetime.combine(d, datetime.min.time())


class EulerpoolFinancialStatementRepository(BaseEulerpoolRepository, FinancialStatementSourcePort):
    """One statement from Eulerpool in canonical form. Subclasses set STATEMENT and FLOW ('quarter' | 'ytd' | None
    for a balance sheet)."""

    STATEMENT: str = ""
    FLOW: Optional[str] = None
    FREQUENCIES = (QUARTERLY, ANNUAL)

    def __init__(self, eulerpool_client, factory=None, fundamentals: Optional[EulerpoolFundamentalsRepository] = None):
        super().__init__(eulerpool_client, factory)
        self.fundamentals = fundamentals or EulerpoolFundamentalsRepository(eulerpool_client, factory)
        self._facts: Dict[Tuple[str, str], List[XBRLFact]] = {}

    @property
    def tag_map(self) -> Dict[str, Tuple[Alternative, ...]]:
        return TAG_MAP[self.STATEMENT]

    def facts(self, symbol: str, fiscal_period: str) -> List[XBRLFact]:
        """The statement's facts of one fiscal period type (cached for the session)."""
        key = (symbol, fiscal_period)
        if key not in self._facts:
            self._facts[key] = self.fundamentals.get_statement(self.STATEMENT, symbol, fiscal_period=fiscal_period)
        return self._facts[key]

    # -- FinancialStatementSourcePort --
    def fetch(self, symbol: str, frequency: str) -> List[StatementRecord]:
        """Every period at that frequency, oldest publication first. Raises EulerpoolError on a failed request."""
        if frequency not in self.FREQUENCIES:
            raise ValueError(f"Eulerpool statements: unknown frequency {frequency!r} (1q | 1y)")
        symbol = symbol.strip().upper()
        annual_facts = self.facts(symbol, "FY")
        # an income statement's annual series also needs its quarters: they tell a full-year 10-K row from a
        # fourth-quarter one (see _repair_years)
        needs_quarters = frequency == QUARTERLY or self.FLOW == "quarter"
        quarterly_facts = [f for p in QUARTER_TYPES for f in self.facts(symbol, p)] if needs_quarters else []
        return self.normalize(symbol, frequency, annual_facts, quarterly_facts)

    # -- normalization (no request) --
    def normalize(self, symbol: str, frequency: str, annual_facts: Sequence[XBRLFact],
                  quarterly_facts: Sequence[XBRLFact] = ()) -> List[StatementRecord]:
        tags = {t for alternatives in self.tag_map.values() for alt in alternatives for _, t in alt}
        annual = [f for f in annual_facts if f.tag in tags and FORMS.get(f.form) == "FY"]
        anchor = self._fiscal_year_end_anchor(annual)
        if anchor is None:
            logger.warning(f"Eulerpool {self.STATEMENT} {symbol}: no 10-K - no fiscal year end, no statement")
            return []
        years = self._periods([f for f in annual if self._is_year_end(f.period_end, anchor)], "FY")
        quarter_facts = [f for f in quarterly_facts if f.tag in tags and FORMS.get(f.form) == "Q"
                         and f.fiscal_period in QUARTER_TYPES and not self._is_year_end(f.period_end, anchor)]
        by_year = self._by_year(years, self._periods(quarter_facts, "Q"), anchor)
        years, fourth = self._repair_years(symbol, years, by_year)
        meta = self._metadata(list(annual_facts) + list(quarterly_facts))
        if frequency == ANNUAL:
            records = [self._record(symbol, ANNUAL, "FY", end, fields, meta) for end, fields in years.items()]
        else:
            records = self._quarterly_records(symbol, years, by_year, fourth, meta)
        return deduplicate([r for r in records if r is not None], "Eulerpool")

    def _by_year(self, years, quarters, anchor) -> Dict[date, Dict[str, Tuple[date, Dict[str, Tuple[_Fact, str]]]]]:
        """{fiscal year end: {'Q1'..'Q3': (period end, fields)}}."""
        year_ends = sorted(years)
        by_year: Dict[date, Dict[str, Tuple[date, Dict[str, Tuple[_Fact, str]]]]] = defaultdict(dict)
        for end, fields in quarters.items():
            label = max((q for _, q in fields.values()), key=lambda q: sum(1 for _, x in fields.values() if x == q))
            fy_end = next((e for e in year_ends if e >= end and (e - end).days < 380), None)
            if fy_end is None:          # the current fiscal year: its 10-K is not out yet
                fy_end = self._next_year_end(end, anchor)
            by_year[fy_end][label] = (end, fields)
        return by_year

    def _repair_years(self, symbol, years, by_year):
        """An income statement 10-K row at the fiscal year end can be the FOURTH QUARTER (Eulerpool keeps one row per
        tag and period end, and a 10-K also tags its quarterly data): revenue below Q1 + Q2 + Q3 gives it away. That
        row is then the fourth quarter as filed, and the year = Q1 + Q2 + Q3 + Q4 (fields reported in all four).
        Returns (years, {fiscal year end: fourth quarter fields})."""
        if self.FLOW != "quarter":
            return years, {}
        years, fourth = dict(years), {}
        for fy_end, fields in list(years.items()):
            items = by_year.get(fy_end, {})
            if "revenue" not in fields or any(q not in items or "revenue" not in items[q][1] for q in QUARTER_TYPES):
                continue
            nine_months = sum(items[q][1]["revenue"][0].value for q in QUARTER_TYPES)
            if nine_months <= 0 or fields["revenue"][0].value >= 0.9 * nine_months:
                continue
            fourth[fy_end] = {name: (fact, "Q4") for name, (fact, _) in fields.items()}
            year = {}
            for name, (fact, _) in fields.items():
                if name in NOT_DERIVED or any(name not in items[q][1] for q in QUARTER_TYPES):
                    continue
                parts = [items[q][1][name][0] for q in QUARTER_TYPES] + [fact]
                year[name] = (_Fact(sum(p.value for p in parts), fact.filed, max(p.available_at for p in parts),
                                    derived=True), "FY")
            logger.info(f"Eulerpool {self.STATEMENT} {symbol}: the 10-K row of the fiscal year ending {fy_end} is its "
                        f"fourth quarter - year rebuilt from the four quarters")
            if year:
                years[fy_end] = year
            else:
                del years[fy_end]
        return years, fourth

    @staticmethod
    def _fiscal_year_end_anchor(annual: Sequence[XBRLFact]) -> Optional[date]:
        """The latest 10-K's own period: the latest period end among the 10-K facts (comparatives are older)."""
        return max((f.period_end for f in annual), default=None)

    @staticmethod
    def _is_year_end(day: date, anchor: date) -> bool:
        for year in (day.year - 1, day.year, day.year + 1):
            try:
                candidate = anchor.replace(year=year)
            except ValueError:                       # 29 February
                candidate = anchor.replace(year=year, day=28)
            if abs((day - candidate).days) <= FISCAL_YEAR_END_TOLERANCE:
                return True
        return False

    def _periods(self, facts: Iterable[XBRLFact], kind: str) -> Dict[date, Dict[str, Tuple[_Fact, str]]]:
        """{period end: {canonical field: (fact, quarter type)}} - per tag the earliest filed fact."""
        by_tag: Dict[Tuple[date, str], XBRLFact] = {}
        for f in facts:
            key = (f.period_end, f.tag)
            kept = by_tag.get(key)
            if kept is None or (f.filed or date.max) < (kept.filed or date.max):
                by_tag[key] = f
        tags_of: Dict[date, Dict[str, XBRLFact]] = defaultdict(dict)
        for (end, tag), f in by_tag.items():
            tags_of[end][tag] = f
        out: Dict[date, Dict[str, Tuple[_Fact, str]]] = {}
        for end, tags in tags_of.items():
            bound = _midnight(end + timedelta(days=DEADLINE_DAYS[kind] + 1))
            fields = {}
            for name, alternatives in self.tag_map.items():
                for alt in alternatives:
                    if all(t in tags for _, t in alt):
                        parts = [tags[t] for _, t in alt]
                        filed = max((p.filed for p in parts if p.filed), default=None)
                        value = sum(sign * tags[t].value for sign, t in alt)
                        fields[name] = (_Fact(value, filed, bound), parts[0].fiscal_period or kind)
                        break
            if fields:
                out[end] = fields
        return out

    @staticmethod
    def _metadata(facts: Sequence[XBRLFact]) -> Dict[str, Optional[str]]:
        units = [f.unit for f in facts if f.unit and "/" not in f.unit and f.unit.lower() != "shares"]
        currency = max(set(units), key=units.count) if units else None
        cik = next((f.cik for f in facts if f.cik), None)
        return {"currency": currency, "cik": cik.zfill(10) if cik and cik.isdigit() else cik}

    def _record(self, symbol: str, frequency: str, period: str, end: date, fields: Dict[str, Tuple[_Fact, str]],
                meta, fiscal_year_end: Optional[date] = None) -> Optional[StatementRecord]:
        if not fields:
            return None
        facts = [f for f, _ in fields.values()]
        filed = max((f.filed for f in facts if f.filed), default=None)
        available_by = max(f.available_at for f in facts)
        return StatementRecord(
            symbol=symbol, statement=self.STATEMENT, frequency=frequency, period=period,
            fiscal_year=(fiscal_year_end or end).year, period_end=end, filing_date=filed, accepted_at=None,
            reported_currency=meta["currency"], cik=meta["cik"],
            values={name: f.value for name, (f, _) in fields.items()}, available_by=available_by)

    def _quarterly_records(self, symbol, years, by_year, fourth, meta) -> List[StatementRecord]:
        """Quarter records Q1..Q4 per fiscal year (see the module docstring for the derivations)."""
        orphans = []
        for fy_end, items in by_year.items():
            for label, (end, fields) in items.items():
                if self.FLOW == "ytd" and label != "Q1":
                    previous = items.get(QUARTER_TYPES[QUARTER_TYPES.index(label) - 1])
                    fields = self._difference(fields, previous[1] if previous else None)
                orphans.append(self._record(symbol, QUARTERLY, label, end, fields, meta, fy_end))
            if fy_end in fourth:
                orphans.append(self._record(symbol, QUARTERLY, "Q4", fy_end, fourth[fy_end], meta, fy_end))
            elif fy_end in years:
                q4 = self._fourth_quarter(years[fy_end], items, fy_end)
                orphans.append(self._record(symbol, QUARTERLY, "Q4", fy_end, q4, meta, fy_end))
        # fiscal years with a 10-K but no quarter in the answers: the balance sheet's Q4 is still the year end
        if self.FLOW is None:
            for fy_end, fields in years.items():
                if fy_end not in by_year:
                    orphans.append(self._record(symbol, QUARTERLY, "Q4", fy_end, fields, meta, fy_end))
        return [r for r in orphans if r is not None]

    @staticmethod
    def _next_year_end(end: date, anchor: date) -> date:
        for year in (end.year, end.year + 1):
            try:
                candidate = anchor.replace(year=year)
            except ValueError:
                candidate = anchor.replace(year=year, day=28)
            if candidate >= end:
                return candidate
        return anchor.replace(year=end.year + 1)

    @staticmethod
    def _difference(current, previous) -> Dict[str, Tuple[_Fact, str]]:
        """Year-to-date -> quarter: current - previous, per field present in both."""
        if not previous:
            return {}
        out = {}
        for name, (fact, label) in current.items():
            if name in previous and name not in NOT_DERIVED:
                before = previous[name][0]
                out[name] = (_Fact(fact.value - before.value, fact.filed,
                                   max(fact.available_at, before.available_at), derived=True), label)
        return out

    def _fourth_quarter(self, year_fields, items, fy_end: date) -> Dict[str, Tuple[_Fact, str]]:
        if self.FLOW is None:
            return dict(year_fields)                 # balance: the year end is the fourth quarter's end
        needed = ("Q3",) if self.FLOW == "ytd" else QUARTER_TYPES
        if any(q not in items for q in needed):
            return {}
        out = {}
        for name, (fact, _) in year_fields.items():
            if name in NOT_DERIVED or any(name not in items[q][1] for q in needed):
                continue
            parts = [items[q][1][name][0] for q in needed]
            stamp = max([fact.available_at] + [p.available_at for p in parts])
            out[name] = (_Fact(fact.value - sum(p.value for p in parts), fact.filed, stamp, derived=True), "Q4")
        revenue = out.get("revenue")
        if revenue is not None and revenue[0].value < 0:
            logger.warning(f"Eulerpool {self.STATEMENT}: fiscal year ending {fy_end} gives a negative fourth-quarter "
                           f"revenue - its quarters are not three-month values; Q4 not derived")
            return {}
        return out


class EulerpoolIncomeStatementRepository(EulerpoolFinancialStatementRepository):
    STATEMENT = INCOME_STATEMENT
    FLOW = "quarter"


class EulerpoolBalanceSheetRepository(EulerpoolFinancialStatementRepository):
    STATEMENT = BALANCE_SHEET
    FLOW = None


class EulerpoolCashFlowStatementRepository(EulerpoolFinancialStatementRepository):
    STATEMENT = CASH_FLOW
    FLOW = "ytd"


STATEMENT_REPOSITORIES = {cls.STATEMENT: cls for cls in (EulerpoolIncomeStatementRepository,
                                                        EulerpoolBalanceSheetRepository,
                                                        EulerpoolCashFlowStatementRepository)}
