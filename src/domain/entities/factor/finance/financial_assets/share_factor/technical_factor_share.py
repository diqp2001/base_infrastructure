# domain/entities/factor/finance/financial_assets/share_factor/technical_factor_share.py

from __future__ import annotations
from typing import Optional
from domain.entities.factor.finance.financial_assets.share_factor.share_factor import FactorShare


class TechnicalFactorShare(FactorShare):
    """A technical indicator factor for equities, parameterized by indicator type and period."""

    def __init__(
        self,
        name: str,
        indicator_type: str,  # e.g., 'RSI', 'Bollinger', 'Stochastic'
        period: Optional[int] = None,
        group: str = "Technical",
        subgroup: Optional[str] = "Oscillators",
        data_type: str = "numeric",
        source: Optional[str] = "Internal",
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
    ):
        definition = definition or f"{indicator_type} technical indicator{f' ({period}-period)' if period else ''}"
        super().__init__(name=name, group=group, subgroup=subgroup, data_type=data_type, source=source, definition=definition, factor_id=factor_id)
        self.indicator_type = indicator_type
        self.period = period

    def __str__(self):
        return f"TechnicalFactorShare(name={self.name}, type={self.indicator_type}, period={self.period})"