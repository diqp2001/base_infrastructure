"""
src/domain/entities/factor/share_momentum_factor.py

ShareMomentumFactor domain entity - follows unified factor pattern.
"""

from __future__ import annotations
from typing import Optional, List, Union
from datetime import timedelta
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
        
        period: Optional[Union[int, timedelta]] = None,
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
        # Support both int (legacy) and timedelta (new) for period
        if isinstance(period, timedelta):
            self.period = period
        elif isinstance(period, int):
            self.period = timedelta(days=period)
        else:
            self.period = timedelta(days=20)  # Default 20-day momentum
        
        self.momentum_type = momentum_type or "price"  # e.g., "price", "returns", "risk_adjusted"

    def calculate_momentum(self, prices: List[float]) -> Optional[float]:
        """
        Calculate momentum based on price history.
        Domain business logic for momentum calculation.
        
        This is the legacy method that works with simple price arrays.
        For date-aware calculations, use calculate_momentum_with_dates.
        """
        if not prices or len(prices) < 2:
            return None if not prices else 0.0

        # Convert timedelta period to approximate number of periods for legacy support
        period_days = self.period.days if isinstance(self.period, timedelta) else self.period
        
        if len(prices) < period_days:
            # If we don't have enough data, use all available data
            past_price = prices[0]
        else:
            past_price = prices[-period_days]
        
        current_price = prices[-1]
        
        if past_price <= 0:
            return None
            
        momentum = (current_price / past_price) - 1
        return momentum
    
    def calculate_momentum_with_dates(self, prices: List[float], dates: List, current_date) -> Optional[float]:
        """
        Calculate momentum using date-aware logic with proper date deltas.
        
        Args:
            prices: List of price values
            dates: List of corresponding dates
            current_date: The current date for momentum calculation
            
        Returns:
            Momentum value or None if insufficient data
        """
        if not prices or not dates or len(prices) != len(dates):
            return None
            
        if len(prices) < 2:
            return 0.0
        
        # Find the start date for our momentum period
        start_date = current_date - self.period
        
        # Find prices within the date range
        current_price = None
        past_price = None
        
        # Get current price (at or before current_date)
        for i in reversed(range(len(dates))):
            if dates[i] <= current_date:
                current_price = prices[i]
                break
        
        # Get past price (closest to start_date)
        for i, date in enumerate(dates):
            if date >= start_date:
                past_price = prices[i]
                break
        
        if current_price is None or past_price is None or past_price <= 0:
            return None
            
        momentum = (current_price / past_price) - 1
        return momentum

    def is_short_term(self) -> bool:
        """Check if this is a short-term momentum factor."""
        period_days = self.period.days if isinstance(self.period, timedelta) else self.period
        return period_days <= 30

    def is_medium_term(self) -> bool:
        """Check if this is a medium-term momentum factor."""
        period_days = self.period.days if isinstance(self.period, timedelta) else self.period
        return 30 < period_days <= 90

    def is_long_term(self) -> bool:
        """Check if this is a long-term momentum factor."""
        period_days = self.period.days if isinstance(self.period, timedelta) else self.period
        return period_days > 90