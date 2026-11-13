"""
src/domain/entities/factor/finance/financial_assets/share_factor/company_share/fundamental/company_share_fundamental_statement_item_factor.py

Statement totals calculated from their components (IDENTITIES of company_share_fundamental_factor), e.g.

    free_cash_flow                    operatingCashFlow + capitalExpenditure   (capital expenditure is negative)
    net_debt                          totalDebt - cashAndCashEquivalents
    gross_profit                      revenue - costOfRevenue
    cost_and_expenses                 operatingExpenses + costOfRevenue
    cash_and_short_term_investments   cashAndCashEquivalents + shortTermInvestments
    goodwill_and_intangible_assets    goodwill + intangibleAssets
    net_change_in_cash                cashAtEndOfPeriod - cashAtBeginningOfPeriod

The provider usually reports the total too: that raw series (e.g. FMP 'freeCashFlow', source 'fmp') is kept as
delivered; this factor (source 'calculated') is the same total built from the components through the factor
dependencies - one definition whatever the provider, and a check of the provider's total. '_ttm' on quarterly
statements: flows over the last four quarters (a balance sheet total is the latest one).
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

from .company_share_fundamental_factor import (
    IDENTITIES, CompanyShareFundamentalFactor, Measure, StatementInput,
)


def _snake(field: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", field).lower()


def _measure(statement: str, total: str, parts: Tuple[Tuple[str, str], ...]) -> Measure:
    inputs = tuple(StatementInput(_snake(f), statement, f) for _, f in parts)
    signs = {_snake(f): (1.0 if sign == "+" else -1.0) for sign, f in parts}
    text = " ".join(f"{'+' if sign == '+' else '-'} {f}" for sign, f in parts).lstrip("+ ")
    return Measure(inputs, lambda v: sum(signs[k] * v[k] for k in signs), f"{total} = {text}")


class CompanyShareFundamentalStatementItemFactor(CompanyShareFundamentalFactor):
    """A statement total from its components (see the module docstring)."""

    KIND = "statement_item"
    MEASURES: Dict[str, Measure] = {_snake(total): _measure(statement, total, parts)
                                    for statement, total, parts in IDENTITIES}

    def __init__(self, name: str = "free_cash_flow", **kwargs):
        super().__init__(name=name, **kwargs)
