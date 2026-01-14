from __future__ import annotations
from typing import Optional
from datetime import date
from decimal import Decimal

from src.domain.entities.finance.financial_assets.derivatives.future.bond_future import BondFuture



class TreasuryBondFuture(BondFuture):
    """Future contract specifically for a Treasury Bond."""

    def __init__(self,  **kwargs):
        super().__init__(**kwargs)
