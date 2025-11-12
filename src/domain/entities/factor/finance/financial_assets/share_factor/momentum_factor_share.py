# domain/entities/factor/finance/financial_assets/share_factor/momentum_factor_share.py

from __future__ import annotations
from typing import Optional
from domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor


class ShareMomentumFactor(ShareFactor):
    """A momentum factor for equities, parameterized by time period (e.g., 21-day momentum)."""

    def __init__(
        self,
        name: str,
        period: int,
        group: str = "Momentum",
        subgroup: Optional[str] = "Return-based",
        data_type: str = "numeric",
        source: Optional[str] = "Internal",
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
    ):
        definition = definition or f"{period}-day momentum return factor"
        super().__init__(name=name, group=group, subgroup=subgroup, data_type=data_type, source=source, definition=definition, factor_id=factor_id)
        self.period = period

    def __str__(self):
        return f"MomentumFactorShare(name={self.name}, period={self.period})"


