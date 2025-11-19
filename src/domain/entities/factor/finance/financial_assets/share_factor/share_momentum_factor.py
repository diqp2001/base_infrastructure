"""
src/domain/entities/factor/share_momentum_factor.py

ShareMomentumFactor domain entity - follows unified factor pattern.
"""

from __future__ import annotations
from typing import Optional, List
from .share_factor import ShareFactor


class ShareMomentumFactor(ShareFactor):
    """Domain entity representing a share momentum factor."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        
        period: Optional[int] = None,
        momentum_type: Optional[str] = None,
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
        self.period = period or 20  # Default 20-day momentum
        self.momentum_type = momentum_type or "price"  # e.g., "price", "returns", "risk_adjusted"

    def calculate_momentum(self, prices: List[float]) -> Optional[float]:
        """
        Calculate momentum based on price history.
        Domain business logic for momentum calculation.
        """
        if not prices or len(prices) < self.period:
            return None

        if len(prices) < 2:
            return 0.0

        # Simple momentum: (current_price / price_N_periods_ago) - 1
        current_price = prices[-1]
        past_price = prices[-self.period] if len(prices) >= self.period else prices[0]
        
        if past_price <= 0:
            return None
            
        momentum = (current_price / past_price) - 1
        return momentum

    def is_short_term(self) -> bool:
        """Check if this is a short-term momentum factor."""
        return self.period <= 30

    def is_medium_term(self) -> bool:
        """Check if this is a medium-term momentum factor."""
        return 30 < self.period <= 90

    def is_long_term(self) -> bool:
        """Check if this is a long-term momentum factor."""
        return self.period > 90