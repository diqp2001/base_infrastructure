from __future__ import annotations
from typing import Optional
from datetime import date
from decimal import Decimal

from src.domain.entities.finance.financial_assets.derivatives.future.bond_future import BondFuture


from ...financial_asset import FinancialAsset
from ...security import Symbol, SecurityType


class TreasuryBondFuture(BondFuture):
    """Future contract specifically for a Treasury Bond."""

    def __init__(
        self,
        treasury_bond_id: int,           # Link to the underlying treasury bond entity
        id: int,
        underlying_asset: FinancialAsset,
        expiration_date: date,
        start_date: date,
        end_date: Optional[date] = None,
        contract_size: Decimal = Decimal("1000"),  # Treasury contracts often have standard face values
        tick_size: Decimal = Decimal("0.015625"),  # 1/64 in decimals
        tick_value: Decimal = Decimal("10"),       # Typically $10 per tick for Treasury futures
        symbol: Optional[Symbol] = None,
    ):
        super().__init__(
            bond_id=treasury_bond_id,
            id=id,
            underlying_asset=underlying_asset,
            expiration_date=expiration_date,
            start_date=start_date,
            end_date=end_date,
            contract_size=contract_size,
            tick_size=tick_size,
            tick_value=tick_value,
            symbol=symbol,
        )
        self.treasury_bond_id = treasury_bond_id
