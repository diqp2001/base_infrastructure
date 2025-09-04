
"""
CompanyStock domain entity representing stocks with company association.
Extends Stock with company-specific functionality.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from .stock import Stock


class CompanyStock(Stock):
    """
    CompanyStock domain entity that links stocks to companies.
    Extends Stock with company-specific functionality.
    """
    
    def __init__(self,
                 id: int,
                 ticker: str,
                 exchange_id: int,
                 company_id: int,
                 start_date: datetime,
                 end_date: Optional[datetime] = None,
                 sector: Optional[str] = None,
                 industry: Optional[str] = None,
                 market_cap: Optional[Decimal] = None,
                 shares_outstanding: Optional[int] = None,
                 leverage: Decimal = Decimal('1.0')):
        """
        Initialize a CompanyStock entity.
        
        Args:
            id: Unique identifier
            ticker: Stock ticker symbol
            exchange_id: Exchange identifier
            company_id: Associated company identifier
            start_date: Data start date
            end_date: Data end date (optional)
            sector: Business sector
            industry: Industry classification
            market_cap: Market capitalization
            shares_outstanding: Number of shares outstanding
            leverage: Trading leverage
        """
        super().__init__(
            id=id,
            ticker=ticker,
            exchange_id=exchange_id,
            start_date=start_date,
            end_date=end_date,
            sector=sector,
            industry=industry,
            market_cap=market_cap,
            shares_outstanding=shares_outstanding,
            leverage=leverage
        )
        
        self.company_id = company_id
    
    @property
    def asset_type(self) -> str:
        """Return asset type for compatibility."""
        return "COMPANY_STOCK"
    
    def is_same_company(self, other: 'CompanyStock') -> bool:
        """Check if this stock belongs to the same company as another."""
        return self.company_id == other.company_id
    
    def get_company_securities(self, all_securities: list) -> list:
        """Get all securities for the same company."""
        return [sec for sec in all_securities 
                if isinstance(sec, CompanyStock) and sec.company_id == self.company_id]
    
    def __repr__(self) -> str:
        return f"CompanyStock({self.ticker}, company_id={self.company_id})"