from typing import Optional
from datetime import date

from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset
from ..derivative import Derivative

from enum import Enum


class Note(Derivative):
    """
    Pure identification Note.
    Greeks, IV, moneyness, etc. live elsewhere (factors).
    """

    def __init__(self,
                 id: int,
                 underlying_asset: FinancialAsset,
                 expiration_date: date,
                 start_date: date,
                 end_date: Optional[date] = None):
        
        super().__init__(id, underlying_asset, start_date, end_date)

        self.expiration_date = expiration_date
