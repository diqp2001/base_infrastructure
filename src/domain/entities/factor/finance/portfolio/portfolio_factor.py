"""
src/domain/entities/factor/portfolio_factor.py

PortfolioFactor domain entity - follows unified factor pattern.
"""

from __future__ import annotations
from typing import Optional

from domain.entities.factor.factor import Factor

# OR import the correct parent below, depending on your hierarchy


class PortfolioFactor(Factor):
    """Domain entity representing a portfolio-specific factor."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
        )
