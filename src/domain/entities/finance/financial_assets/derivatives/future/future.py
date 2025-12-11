
from __future__ import annotations
from typing import Optional
from datetime import date
from decimal import Decimal

from ..derivative import Derivative, UnderlyingAsset
from ...security import Symbol
from domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class Future(Derivative):
    """
    Pure identification Future.
    Margin, daily settlement, and other metrics live elsewhere (factors).
    """

    def __init__(
        self,
        id: int,
        underlying_asset: FinancialAsset,
        expiration_date: date,
        start_date: date,
        end_date: Optional[date] = None,
        contract_size: Decimal = Decimal("1"),
        tick_size: Decimal = Decimal("0.01"),
        tick_value: Decimal = Decimal("1"),
        symbol: Optional[Symbol] = None,
    ):
        super().__init__(id, underlying_asset, start_date, end_date)

        self.expiration_date = expiration_date
        self.contract_size = contract_size
        self.tick_size = tick_size
        self.tick_value = tick_value

        # Symbol can be provided or auto-generated based on underlying
        if symbol is None:
            self.symbol = Symbol(
                ticker=f"{underlying_asset.symbol}_{expiration_date.strftime('%Y%m%d')}",
                exchange="FUTURES",
                security_type="FUTURE"
            )
        else:
            self.symbol = symbol

     