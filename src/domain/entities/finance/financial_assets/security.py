"""
Security base class following QuantConnect Lean architecture patterns.
Provides template method pattern and common functionality for all tradeable securities.
"""


from datetime import date
from typing import Optional
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset




class Security(FinancialAsset):
    """
    Base class for all tradeable securities following QuantConnect architecture.
    Implements template method pattern for market data processing.
    """
    
    def __init__(self,
                 id: int,
                 start_date: date,
                 end_date: Optional[date]):
        
        super().__init__(id, start_date, end_date)
    