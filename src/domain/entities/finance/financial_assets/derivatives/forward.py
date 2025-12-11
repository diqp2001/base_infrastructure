from datetime import date
from typing import Optional
from domain.entities.finance.financial_assets.derivatives.derivative import Derivative
from domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class Future(Derivative):
    """
    Futures contract with exchange link.
    """

    def __init__(self,
                 id: int,
                 underlying_asset: FinancialAsset,
                 expiration_date: date,
                 exchange_id: int,
                 start_date: date,
                 end_date: Optional[date] = None):
        
        super().__init__(id, underlying_asset, start_date, end_date)
        self.expiration_date = expiration_date
        self.exchange_id = exchange_id
