"""
Share class extending Equity following QuantConnect architecture.
Base class for all share-based instruments (CompanyShare, ETFShare, etc).
"""

from abc import ABC
from datetime import datetime
from decimal import Decimal
from typing import Optional
from .equity import Equity, FundamentalData, MarketData
from .security import Symbol, SecurityType


class Share(Equity, ABC):
    """
    Base Share class extending Equity.
    Parent class for CompanyShare, ETFShare, and other share-based instruments.
    """
    
    def __init__(self, id: int, ticker: str, exchange_id: int, 
                 start_date: datetime, end_date: Optional[datetime] = None):
        # Create symbol for base Security class
        symbol = Symbol(
            ticker=ticker,
            exchange=f"EXCHANGE_{exchange_id}",  # Could be enhanced to lookup actual exchange
            security_type=SecurityType.SHARE
        )
        
        super().__init__(symbol)
        
        # Share-specific attributes
        self.id = id
        self.exchange_id = exchange_id
        self.start_date = start_date
        self.end_date = end_date
        
    @property
    def ticker(self) -> str:
        """Get share ticker symbol."""
        return self.symbol.ticker
    
    def update_share_fundamentals(self, fundamentals: FundamentalData) -> None:
        """Update fundamental data with share-specific validation."""
        # Add share-specific validation logic here
        if fundamentals.market_cap and fundamentals.shares_outstanding:
            implied_price = fundamentals.market_cap / Decimal(str(fundamentals.shares_outstanding))
            # Validate that implied price is reasonable compared to current price
            if self.price > 0:
                price_diff = abs(implied_price - self.price) / self.price
                if price_diff > Decimal('0.1'):  # 10% difference threshold
                    print(f"Warning: Market cap implies price {implied_price}, current price {self.price}")
        
        self.update_fundamentals(fundamentals)
    
    def is_active(self) -> bool:
        """Check if the share is currently active/trading."""
        if self.end_date and datetime.now() > self.end_date:
            return False
        return self.is_tradeable
    
    def get_trading_period(self) -> dict:
        """Get the trading period information."""
        return {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'is_active': self.is_active(),
            'trading_days': self._calculate_trading_days()
        }
    
    def _calculate_trading_days(self) -> Optional[int]:
        """Calculate number of trading days since start."""
        if not self.start_date:
            return None
            
        end_date = self.end_date or datetime.now()
        delta = end_date - self.start_date
        
        # Rough calculation: 5/7 of days are trading days
        return int(delta.days * 5/7)
    
    def calculate_market_cap(self) -> Optional[Decimal]:
        """Calculate current market capitalization."""
        if not self.fundamentals or not self.fundamentals.shares_outstanding:
            return None
            
        return self.price * Decimal(str(self.fundamentals.shares_outstanding))
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "Share"
    
    def __str__(self) -> str:
        return f"Share({self.ticker}, ${self.price})"
    
    def __repr__(self) -> str:
        return (f"Share(id={self.id}, ticker={self.ticker}, "
                f"price={self.price}, sector={self.sector})")