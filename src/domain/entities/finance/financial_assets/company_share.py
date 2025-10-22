"""
CompanyShare class linking shares to companies with enhanced domain model.
Replaces CompanyStock - extends Share with company-specific relationships and business logic.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal
from .share import Share, MarketData


class CompanyShare(Share):
    """
    CompanyShare extends Share to link securities with company entities.
    Replaces the previous CompanyStock class with improved architecture.
    Provides company-specific business logic and relationships.
    """
    
    def __init__(self, id: Optional[int], ticker: str, exchange_id: int, company_id: int, 
                 start_date: datetime, end_date: Optional[datetime] = None):
        super().__init__(id, ticker, exchange_id, start_date, end_date)
        
        # Company relationship
        self.company_id = company_id
        self._company_name: Optional[str] = None
        self._sector: Optional[str] = None  # internal storage
        self._industry: Optional[str] = None  # internal storage
        
    @property
    def company_name(self) -> Optional[str]:
        """Get the company name."""
        return self._company_name
    
    def set_company_name(self, name: str) -> None:
        """Set the company name."""
        self._company_name = name
    @property
    def sector(self) -> Optional[str]:
        return self._sector

    def set_sector(self, sector: str) -> None:
        self._sector = sector

    @property
    def industry(self) -> Optional[str]:
        return self._industry

    def set_industry(self, industry: str) -> None:
        self._industry = industry

    
    def update_market_data(self, data: MarketData) -> None:
        """Override to add company-specific market data processing."""
        super().update_market_data(data)
        
        # Company-specific processing could include:
        # - Earnings announcements impact
        # - News sentiment analysis
        # - Peer comparison updates
    
    def get_company_metrics(self) -> dict:
        """Get company-specific basic metrics."""
        return {
            'company_id': self.company_id,
            'company_name': self.company_name,
            'ticker': self.ticker,
            'current_price': self.price,
            'sector': self.sector,
            'industry': self.industry,
        }
    
    # calculate_market_cap removed - use factors instead
    
    # update_company_fundamentals removed - use factors instead
    
    
    def is_active(self) -> bool:
        """Check if the company stock is currently active/trading."""
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
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "CompanyShare"
    
    def __str__(self) -> str:
        return f"CompanyShare({self.ticker}, ${self.price})"
    
    def __repr__(self) -> str:
        """Enhanced representation showing company relationship."""
        company_info = f", company_id={self.company_id}"
        if self.company_name:
            company_info += f", company='{self.company_name}'"
        
        return (f"CompanyShare(id={self.id}, ticker={self.ticker}"
                f"{company_info}, price=${self.price})")


