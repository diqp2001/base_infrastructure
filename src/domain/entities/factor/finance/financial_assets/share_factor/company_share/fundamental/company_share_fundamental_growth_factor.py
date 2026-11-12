"""
src/domain/entities/factor/finance/financial_assets/share_factor/company_share/fundamental/company_share_fundamental_growth_factor.py

Growth of a financial statement item between two fiscal periods (see company_share_fundamental_factor for the
point-in-time rule): Growth(t) = Value(t) / Value(t - lag) - 1, no value when Value(t - lag) is not positive.

    <metric>_growth       lag one period of the factor's frequency: quarter on quarter ('1q'), year on year ('1y')
    <metric>_growth_yoy   quarterly factors only: the same quarter one year earlier (lag four quarters)
    <metric>_growth_ttm   quarterly factors and flows only: the last four quarters summed / the four before - 1

The window must be consecutive periods (Factor.point_in_time_policy max_gap): a missing quarter gives no value.
Metrics: revenue, gross_profit, ebit, ebitda, operating_income, net_income, eps (diluted), free_cash_flow,
operating_cash_flow (flows); total_assets, total_equity, total_debt (balance sheet stocks).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .company_share_fundamental_factor import (
    BALANCE_SHEET, CASH_FLOW, INCOME_STATEMENT, QUARTERLY, QUARTERS_PER_YEAR, CompanyShareFundamentalFactor, Measure,
    StatementInput, growth, is_flow,
)

METRICS: Dict[str, Tuple[str, str]] = {
    "revenue": (INCOME_STATEMENT, "revenue"),
    "gross_profit": (INCOME_STATEMENT, "grossProfit"),
    "ebit": (INCOME_STATEMENT, "ebit"),
    "ebitda": (INCOME_STATEMENT, "ebitda"),
    "operating_income": (INCOME_STATEMENT, "operatingIncome"),
    "net_income": (INCOME_STATEMENT, "netIncome"),
    "eps": (INCOME_STATEMENT, "epsDiluted"),
    "free_cash_flow": (CASH_FLOW, "freeCashFlow"),
    "operating_cash_flow": (CASH_FLOW, "operatingCashFlow"),
    "total_assets": (BALANCE_SHEET, "totalAssets"),
    "total_equity": (BALANCE_SHEET, "totalEquity"),
    "total_debt": (BALANCE_SHEET, "totalDebt"),
}
YOY = "_yoy"


def _measures() -> Dict[str, Measure]:
    out = {}
    for metric, (statement, field) in METRICS.items():
        item = (StatementInput("value", statement, field),)
        out[f"{metric}_growth"] = Measure(item, None, f"{field} growth over one period")
        out[f"{metric}_growth{YOY}"] = Measure(item, None, f"{field} growth on the same quarter one year earlier")
    return out


class CompanyShareFundamentalGrowthFactor(CompanyShareFundamentalFactor):
    """Period-over-period growth of a statement item (see the module docstring)."""

    KIND = "growth"
    MEASURES = _measures()

    def __init__(self, name: str = "revenue_growth", **kwargs):
        super().__init__(name=name, **kwargs)

    @property
    def yoy(self) -> bool:
        return bool(self.measure) and self.measure.endswith(YOY)

    @property
    def item(self) -> Optional[StatementInput]:
        return self.inputs[0] if self.inputs else None

    @property
    def usable(self) -> bool:
        if not super().usable:
            return False
        if self.yoy and (self.ttm or self.frequency != QUARTERLY):
            return False                 # year on year of a yearly series is <metric>_growth
        return not (self.ttm and not is_flow(self.item.statement))   # a stock has no TTM sum

    def window(self) -> Tuple[int, bool]:
        """(lookback, endpoints): two periods `lag` apart, or two consecutive TTM sums."""
        if self.ttm:
            return 2 * QUARTERS_PER_YEAR, False
        return (QUARTERS_PER_YEAR if self.yoy else 1) + 1, True

    @property
    def calculate_dependencies(self) -> list:
        if not self.usable:
            return []
        return [self.statement_spec(self.item, *self.window())]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        if not self.usable:
            return None
        values = [v for v in (dependencies.get(self.item.key) or []) if v is not None]
        lookback, endpoints = self.window()
        if len(values) != (2 if endpoints else lookback):
            return None
        if self.ttm:
            return growth(float(sum(values[QUARTERS_PER_YEAR:])), float(sum(values[:QUARTERS_PER_YEAR])))
        return growth(float(values[-1]), float(values[0]))
