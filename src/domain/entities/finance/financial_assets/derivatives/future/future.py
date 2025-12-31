
from __future__ import annotations
from typing import Optional
from datetime import date
from decimal import Decimal

from domain.entities.finance.exchange import Exchange

from ..derivative import Derivative, UnderlyingAsset

from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class Future(Derivative):
    """
    Pure identification Future.
    Margin, daily settlement, and other metrics live elsewhere (factors).
    """

    def __init__(
        self,
        id: int,
        underlying_asset: FinancialAsset,
        exchange_id :int,
        expiration_date: date,
        start_date: date,
        end_date: Optional[date] = None,
        
    ):
        super().__init__(id, underlying_asset, start_date, end_date)

        self.expiration_date = expiration_date
        self.exchange_id = exchange_id
        

        

     