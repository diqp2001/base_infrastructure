
from __future__ import annotations
from typing import Optional
from datetime import date
from decimal import Decimal

from domain.entities.finance.exchange import Exchange
from domain.entities.finance.financial_assets.currency import Currency

from ..derivative import Derivative

from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class Future(Derivative):
    """
    Pure identification Future.
    Margin, daily settlement, and other metrics live elsewhere (factors).
    """

        
        
        
    def __init__(
                self,
                id: Optional[int],
                name: Optional[str],
                symbol: Optional[str],
                underlying_asset: FinancialAsset,
                currency:Currency,
                exchange :Exchange,
                start_date: Optional[date] = None,
                end_date: Optional[date] = None,
                
            ):

            super().__init__(id =id,underlying_asset = underlying_asset, name=name, symbol=symbol, start_date=start_date, end_date=end_date)
            self.exchange = exchange
            self.currency =currency
            

     