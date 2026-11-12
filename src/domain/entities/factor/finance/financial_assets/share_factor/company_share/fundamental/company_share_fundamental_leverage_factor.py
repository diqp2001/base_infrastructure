"""
src/domain/entities/factor/finance/financial_assets/share_factor/company_share/fundamental/company_share_fundamental_leverage_factor.py

Leverage of a company from its financial statements (see company_share_fundamental_factor for names, inputs and the
point-in-time rule). Net debt to EBITDA is usually read on TTM EBITDA: net_debt_to_ebitda_ttm on quarterly statements.

    debt_to_equity       totalDebt / totalEquity            (balance sheet at the period's end)
    net_debt_to_ebitda   netDebt / ebitda                   (no value on a non-positive EBITDA)
"""

from __future__ import annotations

from .company_share_fundamental_factor import (
    BALANCE_SHEET, INCOME_STATEMENT, CompanyShareFundamentalFactor, Measure, StatementInput, ratio,
)


def _net_debt_to_ebitda(v):
    return None if v["ebitda"] <= 0 else v["net_debt"] / v["ebitda"]


class CompanyShareFundamentalLeverageFactor(CompanyShareFundamentalFactor):
    """Debt multiples of a company share's issuer (see the module docstring)."""

    KIND = "leverage"
    MEASURES = {
        "debt_to_equity": Measure((StatementInput("total_debt", BALANCE_SHEET, "totalDebt"),
                                   StatementInput("total_equity", BALANCE_SHEET, "totalEquity")),
                                  lambda v: ratio(v["total_debt"], v["total_equity"]),
                                  "total debt / total equity"),
        "net_debt_to_ebitda": Measure((StatementInput("net_debt", BALANCE_SHEET, "netDebt"),
                                       StatementInput("ebitda", INCOME_STATEMENT, "ebitda")),
                                      _net_debt_to_ebitda,
                                      "net debt / EBITDA"),
    }

    def __init__(self, name: str = "debt_to_equity", **kwargs):
        super().__init__(name=name, **kwargs)
