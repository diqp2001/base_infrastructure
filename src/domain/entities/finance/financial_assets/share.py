"""
Share class extending Equity following QuantConnect architecture.
Base class for all share-based instruments (CompanyShare, ETFShare, etc).
"""

from abc import ABC
from datetime import datetime
from decimal import Decimal
from typing import Optional
from .equity import Equity, MarketData
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
    
    # update_share_fundamentals removed - use factors instead
    
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
    
    # calculate_market_cap removed - use factors instead
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "Share"
    
    def __str__(self) -> str:
        return f"Share({self.ticker}, ${self.price})"
    
    def __repr__(self) -> str:
        return (f"Share(id={self.id}, ticker={self.ticker}, "
                f"price={self.price}, sector={self.sector})")