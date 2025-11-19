"""
src/domain/entities/factor/share_technical_factor.py

ShareTechnicalFactor domain entity - follows unified factor pattern.
"""

from __future__ import annotations
from typing import Optional, List
from .share_factor import ShareFactor


class ShareTechnicalFactor(ShareFactor):
    """Domain entity representing a share technical analysis factor."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
     
     
        indicator_type: Optional[str] = None,
        period: Optional[int] = None,
        smoothing_factor: Optional[float] = None,
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
        self.indicator_type = indicator_type or "sma"  # e.g., "sma", "ema", "rsi", "macd", "bollinger"
        self.period = period or 20  # Default 20-period
        self.smoothing_factor = smoothing_factor  # For EMA and other smoothed indicators

    def calculate_sma(self, prices: List[float]) -> Optional[float]:
        """Calculate Simple Moving Average."""
        if not prices or len(prices) < self.period:
            return None
        
        recent_prices = prices[-self.period:]
        return sum(recent_prices) / len(recent_prices)

    def calculate_ema(self, prices: List[float], previous_ema: Optional[float] = None) -> Optional[float]:
        """Calculate Exponential Moving Average."""
        if not prices:
            return None
        
        multiplier = 2 / (self.period + 1)
        current_price = prices[-1]
        
        if previous_ema is None:
            # First EMA calculation, use SMA as starting point
            if len(prices) >= self.period:
                return self.calculate_sma(prices)
            else:
                return current_price
        
        return (current_price * multiplier) + (previous_ema * (1 - multiplier))

    def calculate_rsi(self, prices: List[float]) -> Optional[float]:
        """Calculate Relative Strength Index."""
        if not prices or len(prices) < self.period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < self.period:
            return None
        
        avg_gain = sum(gains[-self.period:]) / self.period
        avg_loss = sum(losses[-self.period:]) / self.period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def is_momentum_indicator(self) -> bool:
        """Check if this is a momentum-type technical indicator."""
        momentum_indicators = ["rsi", "macd", "momentum", "roc", "stochastic"]
        return self.indicator_type.lower() in momentum_indicators

    def is_trend_indicator(self) -> bool:
        """Check if this is a trend-following technical indicator."""
        trend_indicators = ["sma", "ema", "adx", "parabolic_sar", "trix"]
        return self.indicator_type.lower() in trend_indicators

    def is_volatility_indicator(self) -> bool:
        """Check if this is a volatility-based technical indicator."""
        volatility_indicators = ["bollinger", "atr", "standard_deviation", "beta"]
        return self.indicator_type.lower() in volatility_indicators