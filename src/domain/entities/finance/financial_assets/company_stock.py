
from .stock import Stock
from typing import Optional
from decimal import Decimal

class CompanyStock(Stock):
    """
    CompanyStock extends Stock with company-specific information and relationships.
    Links financial securities to company entities for fundamental analysis.
    """
    
    def __init__(self, id, ticker, exchange_id, company_id, start_date, end_date, 
                 exchange_name: str = "UNKNOWN", market: str = "USA"):
        super().__init__(id, ticker, exchange_id, start_date, end_date, exchange_name, market)
        
        self.company_id = company_id
        self._company_name: Optional[str] = None
        self._industry: Optional[str] = None
        self._employees_count: Optional[int] = None
        self._headquarters: Optional[str] = None
        
    @property
    def company_name(self) -> Optional[str]:
        return self._company_name
    
    def set_company_name(self, company_name: str) -> None:
        """Set the company name"""
        self._company_name = company_name
    
    @property
    def industry(self) -> Optional[str]:
        return self._industry
    
    def set_industry(self, industry: str) -> None:
        """Set the industry classification"""
        self._industry = industry
    
    @property 
    def employees_count(self) -> Optional[int]:
        return self._employees_count
    
    def set_employees_count(self, count: int) -> None:
        """Set employee count"""
        if count < 0:
            raise ValueError("Employee count cannot be negative")
        self._employees_count = count
    
    @property
    def headquarters(self) -> Optional[str]:
        return self._headquarters
    
    def set_headquarters(self, headquarters: str) -> None:
        """Set headquarters location"""
        self._headquarters = headquarters
    
    def calculate_enterprise_value(self, total_debt: Decimal, cash_equivalents: Decimal) -> Optional[Decimal]:
        """Calculate Enterprise Value = Market Cap + Total Debt - Cash"""
        if self.market_cap is None:
            return None
        return self.market_cap + total_debt - cash_equivalents
    
    def calculate_book_value_per_share(self, total_equity: Decimal, shares_outstanding: Decimal) -> Decimal:
        """Calculate book value per share"""
        if shares_outstanding == 0:
            raise ValueError("Shares outstanding cannot be zero")
        return total_equity / shares_outstanding
    
    def get_fundamental_ratios(self) -> dict:
        """Get key fundamental ratios and metrics"""
        return {
            'pe_ratio': self.pe_ratio,
            'dividend_yield': self.calculate_dividend_yield(),
            'market_cap': self.market_cap,
            'sector': self.sector,
            'industry': self.industry,
            'current_price': self.current_price
        }
    
    def __repr__(self):
        return f"CompanyStock({self.ticker}, company_id={self.company_id}, price={self.current_price})"