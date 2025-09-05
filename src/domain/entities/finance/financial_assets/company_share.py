"""
CompanyShare class linking shares to companies with enhanced domain model.
Replaces CompanyStock - extends Share with company-specific relationships and business logic.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal
from .share import Share, FundamentalData, MarketData


class CompanyShare(Share):
    """
    CompanyShare extends Share to link securities with company entities.
    Replaces the previous CompanyStock class with improved architecture.
    Provides company-specific business logic and relationships.
    """
    
    def __init__(self, id: int, ticker: str, exchange_id: int, company_id: int, 
                 start_date: datetime, end_date: Optional[datetime] = None):
        super().__init__(id, ticker, exchange_id, start_date, end_date)
        
        # Company relationship
        self.company_id = company_id
        self._company_name: Optional[str] = None
        
    @property
    def company_name(self) -> Optional[str]:
        """Get the company name."""
        return self._company_name
    
    def set_company_name(self, name: str) -> None:
        """Set the company name."""
        self._company_name = name
    
    def update_market_data(self, data: MarketData) -> None:
        """Override to add company-specific market data processing."""
        super().update_market_data(data)
        
        # Company-specific processing could include:
        # - Earnings announcements impact
        # - News sentiment analysis
        # - Peer comparison updates
    
    def get_company_metrics(self) -> dict:
        """Get company-specific financial metrics."""
        metrics = {
            'company_id': self.company_id,
            'company_name': self.company_name,
            'ticker': self.ticker,
            'current_price': self.price,
            'market_cap': None,
            'pe_ratio': None,
            'dividend_yield': None,
            'sector': self.sector,
            'industry': self.industry,
        }
        
        if self.fundamentals:
            metrics.update({
                'market_cap': self.fundamentals.market_cap,
                'pe_ratio': self.fundamentals.pe_ratio,
                'dividend_yield': self.fundamentals.dividend_yield,
                'shares_outstanding': self.fundamentals.shares_outstanding,
                'book_value_per_share': self.fundamentals.book_value_per_share,
                'earnings_per_share': self.fundamentals.earnings_per_share,
            })
        
        return metrics
    
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


# Maintain backwards compatibility with CompanyStock
class CompanyStock(CompanyShare):
    """Legacy alias for backwards compatibility."""
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "CompanyStock"
    
    def __str__(self) -> str:
        return f"CompanyStock({self.ticker}, ${self.price})"
    
    def __repr__(self) -> str:
        """Enhanced representation showing company relationship."""
        company_info = f", company_id={self.company_id}"
        if self.company_name:
            company_info += f", company='{self.company_name}'"
        
        return (f"CompanyStock(id={self.id}, ticker={self.ticker}"
                f"{company_info}, price=${self.price})")