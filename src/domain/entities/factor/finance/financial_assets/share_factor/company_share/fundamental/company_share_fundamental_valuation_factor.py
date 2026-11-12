"""
src/domain/entities/factor/finance/financial_assets/share_factor/company_share/fundamental/company_share_fundamental_valuation_factor.py

Valuation of a company share: its latest statements (as of the decision time - see company_share_fundamental_factor)
against its daily close at that time (CompanyShareFactor 'close', group 'price', frequency '1d': the latest closed bar,
read in the source policy's series order).

    earnings_yield   epsDiluted / close
    fcf_yield        freeCashFlow / (close x weightedAverageShsOutDil)

Use the '_ttm' names on quarterly statements for a year of earnings / cash flow. The share count is the period's
weighted average diluted shares (the statements carry no count at the decision time).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .company_share_fundamental_factor import (
    CASH_FLOW, INCOME_STATEMENT, CompanyShareFundamentalFactor, Measure, StatementInput, ratio,
)

CLOSE_KEY = "close"


def _fcf_yield(v: Dict[str, float]) -> Optional[float]:
    if v["shares"] <= 0:
        return None
    return ratio(v["free_cash_flow"], v[CLOSE_KEY] * v["shares"])


class CompanyShareFundamentalValuationFactor(CompanyShareFundamentalFactor):
    """Earnings and free cash flow yields of a company share (see the module docstring)."""

    KIND = "valuation"
    MEASURES = {
        "earnings_yield": Measure((StatementInput("eps", INCOME_STATEMENT, "epsDiluted"),),
                                  lambda v: ratio(v["eps"], v[CLOSE_KEY]),
                                  "earnings yield: diluted EPS / close"),
        "fcf_yield": Measure((StatementInput("free_cash_flow", CASH_FLOW, "freeCashFlow"),
                              StatementInput("shares", INCOME_STATEMENT, "weightedAverageShsOutDil", "latest")),
                             _fcf_yield,
                             "free cash flow yield: free cash flow / (close x diluted shares)"),
    }

    def __init__(self, name: str = "earnings_yield", **kwargs):
        super().__init__(name=name, **kwargs)

    def lookback(self, item: StatementInput):
        if item.how == "latest":
            return None, False          # a count at the period's end, never summed over a TTM window
        return super().lookback(item)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
            CompanyShareFactor,
        )
        specs = super().calculate_dependencies
        if not specs:
            return []
        return specs + [DependencySpec(factor_type=CompanyShareFactor, group="price", frequency="1d",
                                       name_in=["close"], key=CLOSE_KEY, source_not_in=["calculated"])]

    def input_values(self, dependencies: Dict[str, Any]) -> Optional[Dict[str, float]]:
        values = super().input_values(dependencies)
        closes = [c for c in (dependencies.get(CLOSE_KEY) or []) if c is not None]
        if values is None or not closes:
            return None
        return {**values, CLOSE_KEY: float(closes[-1])}
