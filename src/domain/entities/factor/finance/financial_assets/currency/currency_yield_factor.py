"""
CurrencyYieldFactor — the repo (risk-free) yield of a Currency asset.

Represents the short-term interest rate / overnight repo rate for a given currency
(e.g. SOFR for USD, ESTR for EUR, SONIA for GBP). Fetched directly from IBKR.
"""

from __future__ import annotations
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.currency.currency_factor import CurrencyFactor


class CurrencyYieldFactor(CurrencyFactor):
    """
    Domain entity representing the repo (risk-free) yield of a currency.

    This is a leaf factor resolved via IBKR (Branch B). It carries no
    calculate_dependencies and does not implement calculate().
    """

    def __init__(
        self,
        name: str = "currency_yield",
        group: str = "fundamental",
        subgroup: Optional[str] = "yield",
        frequency: Optional[str] = "1d",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "ibkr",
        definition: Optional[str] = "Short-term repo / risk-free yield for the currency",
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            frequency=frequency,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
        )

    def __repr__(self):
        return (
            f"CurrencyYieldFactor(name={self.name!r}, group={self.group!r}, "
            f"subgroup={self.subgroup!r})"
        )
