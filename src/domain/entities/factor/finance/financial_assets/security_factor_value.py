"""
Domain entity for SecurityFactorValue.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
from domain.entities.factor.finance.financial_assets.financial_asset_factor_value import FinancialAssetFactorValue


@dataclass
class SecurityFactorValue(FinancialAssetFactorValue):
    """
    Domain entity representing a security-specific factor value.
    Extends FinancialAssetFactorValue with security-specific business logic.
    """
    security_type: Optional[str] = None  # e.g., "stock", "bond", "etf", "mutual_fund"
    ticker_symbol: Optional[str] = None  # e.g., "AAPL", "GOOGL", "MSFT"
    exchange: Optional[str] = None  # e.g., "NYSE", "NASDAQ", "LSE"
    volume: Optional[Decimal] = None  # trading volume
    
    def __post_init__(self):
        """Validate domain constraints including security-specific ones."""
        super().__post_init__()
        
        if self.volume is not None and not isinstance(self.volume, Decimal):
            self.volume = Decimal(str(self.volume))
        
        if self.ticker_symbol and len(self.ticker_symbol.strip()) == 0:
            raise ValueError("ticker_symbol cannot be empty")

    def calculate_volume_weighted_price(self, volume: Decimal) -> Decimal:
        """Calculate volume-weighted average price."""
        if volume <= 0:
            raise ValueError("Volume must be positive")
        
        return self.value * volume

    def apply_stock_split(self, split_ratio: Decimal) -> 'SecurityFactorValue':
        """Apply stock split adjustment."""
        if split_ratio <= 0:
            raise ValueError("Split ratio must be positive")
        
        return SecurityFactorValue(
            id=self.id,
            factor_id=self.factor_id,
            entity_id=self.entity_id,
            date=self.date,
            value=self.value / split_ratio,  # Price decreases by split ratio
            asset_class=self.asset_class,
            market_value=self.market_value,  # Market value remains the same
            currency=self.currency,
            is_adjusted=True,
            security_type=self.security_type,
            ticker_symbol=self.ticker_symbol,
            exchange=self.exchange,
            volume=self.volume * split_ratio if self.volume else None  # Volume increases
        )

    def calculate_market_cap(self, shares_outstanding: Decimal) -> Optional[Decimal]:
        """Calculate market capitalization if this is a price factor."""
        if shares_outstanding <= 0:
            raise ValueError("Shares outstanding must be positive")
        
        return self.value * shares_outstanding

    def is_liquid_security(self, min_volume_threshold: Decimal = Decimal('10000')) -> bool:
        """Check if security meets liquidity threshold based on volume."""
        if self.volume is None:
            return False
        
        return self.volume >= min_volume_threshold

    def __str__(self) -> str:
        return f"SecurityFactorValue(factor_id={self.factor_id}, entity_id={self.entity_id}, ticker_symbol={self.ticker_symbol}, exchange={self.exchange}, value={self.value})"