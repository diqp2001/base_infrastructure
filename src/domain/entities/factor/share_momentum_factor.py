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
        asset_class: Optional[str] = "equity",
        currency: Optional[str] = None,
        market: Optional[str] = None,
        security_type: Optional[str] = "stock",
        isin: Optional[str] = None,
        cusip: Optional[str] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        market_cap_category: Optional[str] = None,
        ticker_symbol: Optional[str] = None,
        share_class: Optional[str] = None,
        exchange: Optional[str] = None,
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
            asset_class=asset_class,
            currency=currency,
            market=market,
            security_type=security_type,
            isin=isin,
            cusip=cusip,
            sector=sector,
            industry=industry,
            market_cap_category=market_cap_category,
            ticker_symbol=ticker_symbol,
            share_class=share_class,
            exchange=exchange,
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