"""
src/domain/entities/factor/finance/financial_assets/share_factor/company_share/fundamental/company_share_fundamental_factor.py

Company financial statement factors of a CompanyShare (group 'fundamental').

Raw statement fields are CompanyShareFactor series - one per provider field, no class of their own:
    name       the canonical field (STATEMENT_FIELDS, spelled as FMP's statements: 'revenue', 'netIncome', ...); each
               provider maps its own response into it (Eulerpool: SEC XBRL tags)
    group      'fundamental'
    subgroup   the statement: 'income_statement' | 'balance_sheet' | 'cash_flow'
    frequency  the fiscal period: '1q' (quarters Q1..Q4) | '1y' (fiscal years)
    source     the provider ('fmp', 'eulerpool')
A value is stored at the moment its filing became public (the acceptance time; the filing date's end when the
provider gives no acceptance time) - never at the fiscal period's end - and is read as of a decision time
(Factor.point_in_time_policy: the latest value accepted by then). The filing's own data are series of the same
statement stamped at the same time (METADATA_FIELDS): the period's end ('date'), 'filingDate', 'acceptedDate',
'fiscalYear', 'period' (Q1..Q4 | FY), 'reportedCurrency', 'cik'.

Calculated factors - this class's subclasses, each its own class / ORM identity (group 'fundamental', subgroup = KIND):
    CompanyShareFundamentalProfitabilityFactor   margins, ROE, ROA, ROIC
    CompanyShareFundamentalLeverageFactor        debt to equity, net debt to EBITDA
    CompanyShareFundamentalGrowthFactor          <metric>_growth, <metric>_growth_yoy, <metric>_growth_ttm
    CompanyShareFundamentalValuationFactor       earnings yield, free cash flow yield
Name: the measure, optionally suffixed '_ttm' on a quarterly ('1q') factor: income and cash flow items summed over
the last four quarters, balance sheet averages taken over those four quarters. The frequency of a calculated factor is
the statements' frequency it reads (DependencySpec.SELF). A row whose name is not one of the class's measures
decodes with no measure, no dependencies and no value; a missing input or a meaningless denominator (zero or
negative) gives no value - never a default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
    CompanyShareFactor,
)

GROUP = "fundamental"
INCOME_STATEMENT, BALANCE_SHEET, CASH_FLOW = "income_statement", "balance_sheet", "cash_flow"
QUARTERLY, ANNUAL = "1q", "1y"
TTM_SUFFIX = "_ttm"
QUARTERS_PER_YEAR = 4
# the providers of raw statement series (Factor.SOURCES keys), in order of preference: a dependency reads these only
# (never a calculated row), ONE provider per value - the first whose series yields the whole window (the resolver
# reads them in this order and creates the series of an enabled provider that has none yet). FMP first (exact
# acceptance times), Eulerpool (SEC XBRL, SEC-deadline availability) when FMP has nothing for the share.
STATEMENT_SOURCES: Tuple[str, ...] = ("fmp", "eulerpool")

# the canonical statement fields (named as FMP's /stable statements; every provider maps into them), stored as raw CompanyShareFactor series
STATEMENT_FIELDS: Dict[str, Tuple[str, ...]] = {
    INCOME_STATEMENT: (
        "revenue", "costOfRevenue", "grossProfit",
        "researchAndDevelopmentExpenses", "generalAndAdministrativeExpenses", "sellingAndMarketingExpenses",
        "sellingGeneralAndAdministrativeExpenses", "otherExpenses", "operatingExpenses", "costAndExpenses",
        "netInterestIncome", "interestIncome", "interestExpense", "depreciationAndAmortization", "ebitda", "ebit",
        "nonOperatingIncomeExcludingInterest", "operatingIncome", "totalOtherIncomeExpensesNet",
        "incomeBeforeTax", "incomeTaxExpense",
        "netIncomeFromContinuingOperations", "netIncomeFromDiscontinuedOperations", "otherAdjustmentsToNetIncome",
        "netIncome", "netIncomeDeductions", "bottomLineNetIncome",
        "eps", "epsDiluted", "weightedAverageShsOut", "weightedAverageShsOutDil",
    ),
    BALANCE_SHEET: (
        "cashAndCashEquivalents", "shortTermInvestments", "cashAndShortTermInvestments",
        "netReceivables", "accountsReceivables", "otherReceivables", "inventory", "prepaids", "otherCurrentAssets",
        "totalCurrentAssets", "propertyPlantEquipmentNet", "goodwill", "intangibleAssets",
        "goodwillAndIntangibleAssets", "longTermInvestments", "taxAssets", "otherNonCurrentAssets",
        "totalNonCurrentAssets", "otherAssets", "totalAssets",
        "totalPayables", "accountPayables", "otherPayables", "accruedExpenses", "shortTermDebt",
        "capitalLeaseObligationsCurrent", "taxPayables", "deferredRevenue", "otherCurrentLiabilities",
        "totalCurrentLiabilities", "longTermDebt", "capitalLeaseObligationsNonCurrent", "deferredRevenueNonCurrent",
        "deferredTaxLiabilitiesNonCurrent", "otherNonCurrentLiabilities", "totalNonCurrentLiabilities",
        "otherLiabilities", "capitalLeaseObligations", "totalLiabilities",
        "treasuryStock", "preferredStock", "commonStock", "retainedEarnings", "additionalPaidInCapital",
        "accumulatedOtherComprehensiveIncomeLoss", "otherTotalStockholdersEquity", "totalStockholdersEquity",
        "totalEquity", "minorityInterest", "totalLiabilitiesAndTotalEquity",
        "totalInvestments", "totalDebt", "netDebt",
    ),
    CASH_FLOW: (
        "netIncome", "depreciationAndAmortization", "deferredIncomeTax", "stockBasedCompensation",
        "changeInWorkingCapital", "accountsReceivables", "inventory", "accountsPayables", "otherWorkingCapital",
        "otherNonCashItems", "netCashProvidedByOperatingActivities",
        "investmentsInPropertyPlantAndEquipment", "acquisitionsNet", "purchasesOfInvestments",
        "salesMaturitiesOfInvestments", "otherInvestingActivities", "netCashProvidedByInvestingActivities",
        "netDebtIssuance", "longTermNetDebtIssuance", "shortTermNetDebtIssuance",
        "netStockIssuance", "netCommonStockIssuance", "commonStockIssuance", "commonStockRepurchased",
        "netPreferredStockIssuance", "netDividendsPaid", "commonDividendsPaid", "preferredDividendsPaid",
        "otherFinancingActivities", "netCashProvidedByFinancingActivities", "effectOfForexChangesOnCash",
        "netChangeInCash", "cashAtEndOfPeriod", "cashAtBeginningOfPeriod",
        "operatingCashFlow", "capitalExpenditure", "freeCashFlow", "incomeTaxesPaid", "interestPaid",
    ),
}

# the filing's data, stored on every statement at the filing's time: name -> data type
METADATA_FIELDS: Dict[str, str] = {
    "date": "string",               # the fiscal period's end (ISO date)
    "filingDate": "string",         # ISO date
    "acceptedDate": "string",       # ISO date and time (the stamp of the filing's values)
    "fiscalYear": "integer",
    "period": "string",             # Q1..Q4 | FY
    "reportedCurrency": "string",
    "cik": "string",
}

# income and cash flow items are flows over the period; balance sheet items are stocks at the period's end
FLOW_STATEMENTS = frozenset({INCOME_STATEMENT, CASH_FLOW})

# the identities between provider fields (documentation and data checks - each field is stored as delivered)
IDENTITIES: Tuple[Tuple[str, str, Tuple[Tuple[str, str], ...]], ...] = (
    (INCOME_STATEMENT, "grossProfit", (("+", "revenue"), ("-", "costOfRevenue"))),
    (INCOME_STATEMENT, "costAndExpenses", (("+", "operatingExpenses"), ("+", "costOfRevenue"))),
    (BALANCE_SHEET, "cashAndShortTermInvestments", (("+", "cashAndCashEquivalents"), ("+", "shortTermInvestments"))),
    (BALANCE_SHEET, "goodwillAndIntangibleAssets", (("+", "goodwill"), ("+", "intangibleAssets"))),
    (BALANCE_SHEET, "netDebt", (("+", "totalDebt"), ("-", "cashAndCashEquivalents"))),
    (CASH_FLOW, "freeCashFlow", (("+", "operatingCashFlow"), ("+", "capitalExpenditure"))),
    (CASH_FLOW, "netChangeInCash", (("+", "cashAtEndOfPeriod"), ("-", "cashAtBeginningOfPeriod"))),
)


def is_flow(statement: str) -> bool:
    return statement in FLOW_STATEMENTS


@dataclass(frozen=True)
class StatementInput:
    """One statement field a measure reads, under `key` in calculate(dependencies).

    how: 'period'  the latest period's value (a flow: TTM sums the last four quarters)
         'average' the average of the period's opening and closing values (a stock: TTM averages the stock four
                   quarters ago and now)"""
    key: str
    statement: str
    field: str
    how: str = "period"


@dataclass(frozen=True)
class Measure:
    inputs: Tuple[StatementInput, ...]
    formula: Callable[[Dict[str, float]], Optional[float]]
    description: str


def ratio(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """numerator / denominator; None when either is missing or the denominator is not positive (a margin on no
    revenue, a return on negative equity or a multiple of negative EBITDA has no meaning)."""
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def growth(current: Optional[float], base: Optional[float]) -> Optional[float]:
    """current / base - 1; None when the base is missing or not positive (a growth from a loss has no sign)."""
    if current is None or base is None or base <= 0:
        return None
    return current / base - 1.0


class CompanyShareFundamentalFactor(CompanyShareFactor):
    """Base of the calculated fundamental factors (see the module docstring). Subclasses set KIND and MEASURES."""

    KIND: str = ""
    MEASURES: Dict[str, Measure] = {}

    def __init__(self, name: str, group: str = GROUP, subgroup: Optional[str] = None,
                 frequency: Optional[str] = QUARTERLY, data_type: Optional[str] = "numeric",
                 source: Optional[str] = "calculated", definition: Optional[str] = None,
                 factor_id: Optional[int] = None, **kwargs):
        measure, ttm = self.parse_name(name)
        super().__init__(name=name, group=group, subgroup=subgroup or self.KIND, frequency=frequency,
                         data_type=data_type, source=source, factor_id=factor_id,
                         definition=definition or self.describe(measure, ttm) or name)
        self.measure = measure
        self.ttm = ttm

    # -- names --
    @classmethod
    def parse_name(cls, name: str) -> Tuple[Optional[str], bool]:
        """(measure, ttm) of a factor name, or (None, False) for a name that is not one of the class's measures."""
        name = name or ""
        ttm = name.endswith(TTM_SUFFIX) and name[:-len(TTM_SUFFIX)] in cls.MEASURES
        measure = name[:-len(TTM_SUFFIX)] if ttm else name
        return (measure, ttm) if measure in cls.MEASURES else (None, False)

    @classmethod
    def factor_names(cls, ttm: bool = False) -> List[str]:
        return [m + (TTM_SUFFIX if ttm else "") for m in cls.MEASURES]

    @classmethod
    def describe(cls, measure: Optional[str], ttm: bool) -> Optional[str]:
        if not measure:
            return None
        return cls.MEASURES[measure].description + (" (trailing twelve months)" if ttm else "")

    @property
    def usable(self) -> bool:
        """A known measure, and TTM only on quarterly statements."""
        return bool(self.measure) and (not self.ttm or self.frequency == QUARTERLY)

    # -- inputs --
    def lookback(self, item: StatementInput) -> Tuple[Optional[int], bool]:
        """(lookback, endpoints) of the dependency on one statement field."""
        if item.how == "average":
            return (QUARTERS_PER_YEAR + 1 if self.ttm else 2), True
        if self.ttm and is_flow(item.statement):
            return QUARTERS_PER_YEAR, False
        return None, False

    def statement_spec(self, item: StatementInput, lookback: Optional[int] = None, endpoints: bool = False):
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return DependencySpec(factor_type=CompanyShareFactor, group=GROUP, subgroup=item.statement,
                              frequency=DependencySpec.SELF, name_in=[item.field], key=item.key,
                              source_in=list(STATEMENT_SOURCES), lookback=lookback, endpoints=endpoints)

    @property
    def inputs(self) -> Tuple[StatementInput, ...]:
        return self.MEASURES[self.measure].inputs if self.measure else ()

    @property
    def calculate_dependencies(self) -> list:
        if not self.usable:
            return []
        return [self.statement_spec(item, *self.lookback(item)) for item in self.inputs]

    def input_value(self, item: StatementInput, dependencies: Dict[str, Any]) -> Optional[float]:
        """The value of one input from its dependency series (oldest first)."""
        values = [v for v in (dependencies.get(item.key) or []) if v is not None]
        lookback, _ = self.lookback(item)
        if not values or (lookback and len(values) < (2 if item.how == "average" else lookback)):
            return None
        if item.how == "average":
            return (float(values[0]) + float(values[-1])) / 2.0
        if lookback:                                    # a TTM flow: the last four quarters
            return float(sum(values[-lookback:]))
        return float(values[-1])

    def input_values(self, dependencies: Dict[str, Any]) -> Optional[Dict[str, float]]:
        values = {item.key: self.input_value(item, dependencies) for item in self.inputs}
        return None if any(v is None for v in values.values()) else values

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        if not self.usable:
            return None
        values = self.input_values(dependencies)
        if values is None:
            return None
        return self.MEASURES[self.measure].formula(values)
