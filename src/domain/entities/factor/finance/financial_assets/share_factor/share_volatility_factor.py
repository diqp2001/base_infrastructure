"""
src/domain/entities/factor/share_volatility_factor.py

ShareVolatilityFactor domain entity - follows unified factor pattern.
"""

from __future__ import annotations
from typing import Optional, List
import math
from .share_factor import ShareFactor


class ShareVolatilityFactor(ShareFactor):
    """Domain entity representing a share volatility factor."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        
        volatility_type: Optional[str] = None,
        period: Optional[int] = None,
        annualization_factor: Optional[float] = None,
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
        self.volatility_type = volatility_type or "historical"  # e.g., "historical", "realized", "implied"
        self.period = period or 20  # Default 20-day volatility
        self.annualization_factor = annualization_factor or math.sqrt(252)  # Annualize assuming 252 trading days

    def calculate_historical_volatility(self, prices: List[float]) -> Optional[float]:
        """Calculate historical volatility from price series."""
        if not prices or len(prices) < 2:
            return None
        
        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                returns.append(math.log(prices[i] / prices[i-1]))
        
        if len(returns) < self.period:
            return None
        
        # Use most recent returns for calculation
        recent_returns = returns[-self.period:]
        
        # Calculate standard deviation
        mean_return = sum(recent_returns) / len(recent_returns)
        variance = sum((r - mean_return) ** 2 for r in recent_returns) / (len(recent_returns) - 1)
        
        if variance < 0:
            return None
        
        daily_volatility = math.sqrt(variance)
        
        # Annualize if requested
        return daily_volatility * self.annualization_factor

    def calculate_realized_volatility(self, intraday_returns: List[float]) -> Optional[float]:
        """Calculate realized volatility from high-frequency intraday returns."""
        if not intraday_returns:
            return None
        
        # Sum of squared returns
        sum_squared_returns = sum(r ** 2 for r in intraday_returns)
        
        # Realized volatility is the square root of sum of squared returns
        return math.sqrt(sum_squared_returns)

    def calculate_volatility_percentile(self, current_volatility: float, historical_volatilities: List[float]) -> Optional[float]:
        """Calculate the percentile rank of current volatility vs historical values."""
        if not historical_volatilities or current_volatility is None:
            return None
        
        sorted_vols = sorted(historical_volatilities)
        rank = 0
        
        for vol in sorted_vols:
            if current_volatility > vol:
                rank += 1
            else:
                break
        
        percentile = rank / len(sorted_vols) * 100
        return percentile

    def is_high_volatility(self, threshold: float = 0.3) -> bool:
        """Check if this represents a high volatility measurement."""
        # This would need actual volatility value to determine
        return self.volatility_type in ["high", "extreme"]

    def is_annualized(self) -> bool:
        """Check if this volatility factor is annualized."""
        return self.annualization_factor is not None and self.annualization_factor != 1.0

    def is_intraday_volatility(self) -> bool:
        """Check if this measures intraday volatility."""
        return self.volatility_type.lower() in ["realized", "intraday", "high_frequency"]