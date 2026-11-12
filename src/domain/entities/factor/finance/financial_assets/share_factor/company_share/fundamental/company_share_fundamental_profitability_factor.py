"""
src/domain/entities/factor/finance/financial_assets/share_factor/company_share/fundamental/company_share_fundamental_profitability_factor.py

Profitability of a company from its financial statements (see company_share_fundamental_factor for names, inputs and
the point-in-time rule). Quarterly factors without '_ttm' relate one quarter's flow to the capital (not annualized).

    gross_margin       grossProfit / revenue
    operating_margin   operatingIncome / revenue
    ebitda_margin      ebitda / revenue
    net_margin         netIncome / revenue
    fcf_margin         freeCashFlow / revenue
    roe                netIncome / average totalStockholdersEquity (the parent's net income over the parent's equity)
    roa                netIncome / average totalAssets
    roic               ebit x (1 - incomeTaxExpense / incomeBeforeTax)
                       / average (totalDebt + totalEquity - cashAndCashEquivalents)
"""

from __future__ import annotations

from typing import Dict, Optional

from .company_share_fundamental_factor import (
    BALANCE_SHEET, CASH_FLOW, INCOME_STATEMENT, CompanyShareFundamentalFactor, Measure, StatementInput, ratio,
)

REVENUE = StatementInput("revenue", INCOME_STATEMENT, "revenue")
NET_INCOME = StatementInput("net_income", INCOME_STATEMENT, "netIncome")


def _margin(key: str, statement: str, field: str, label: str) -> Measure:
    return Measure((StatementInput(key, statement, field), REVENUE), lambda v: ratio(v[key], v["revenue"]),
                   f"{label} / revenue")


def _roic(v: Dict[str, float]) -> Optional[float]:
    if v["income_before_tax"] <= 0:
        return None                     # no meaningful tax rate on a pre-tax loss
    nopat = v["ebit"] * (1.0 - v["income_tax_expense"] / v["income_before_tax"])
    return ratio(nopat, v["total_debt"] + v["total_equity"] - v["cash"])


class CompanyShareFundamentalProfitabilityFactor(CompanyShareFundamentalFactor):
    """Margins and returns on capital of a company share's issuer (see the module docstring)."""

    KIND = "profitability"
    MEASURES = {
        "gross_margin": _margin("gross_profit", INCOME_STATEMENT, "grossProfit", "gross profit"),
        "operating_margin": _margin("operating_income", INCOME_STATEMENT, "operatingIncome", "operating income"),
        "ebitda_margin": _margin("ebitda", INCOME_STATEMENT, "ebitda", "EBITDA"),
        "net_margin": _margin("net_income", INCOME_STATEMENT, "netIncome", "net income"),
        "fcf_margin": _margin("free_cash_flow", CASH_FLOW, "freeCashFlow", "free cash flow"),
        "roe": Measure((NET_INCOME, StatementInput("equity", BALANCE_SHEET, "totalStockholdersEquity", "average")),
                       lambda v: ratio(v["net_income"], v["equity"]),
                       "return on equity: net income / average stockholders' equity"),
        "roa": Measure((NET_INCOME, StatementInput("assets", BALANCE_SHEET, "totalAssets", "average")),
                       lambda v: ratio(v["net_income"], v["assets"]),
                       "return on assets: net income / average total assets"),
        "roic": Measure((StatementInput("ebit", INCOME_STATEMENT, "ebit"),
                         StatementInput("income_tax_expense", INCOME_STATEMENT, "incomeTaxExpense"),
                         StatementInput("income_before_tax", INCOME_STATEMENT, "incomeBeforeTax"),
                         StatementInput("total_debt", BALANCE_SHEET, "totalDebt", "average"),
                         StatementInput("total_equity", BALANCE_SHEET, "totalEquity", "average"),
                         StatementInput("cash", BALANCE_SHEET, "cashAndCashEquivalents", "average")),
                        _roic,
                        "return on invested capital: EBIT after tax / average (debt + equity - cash)"),
    }

    def __init__(self, name: str = "gross_margin", **kwargs):
        super().__init__(name=name, **kwargs)
