"""
Swap classes for swap contracts.
Includes Interest Rate Swaps, Currency Swaps, and other swap instruments.
"""

from typing import Optional, List, Dict
from datetime import date
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from domain.entities.finance.financial_assets.financial_asset import FinancialAsset
from .derivative import Derivative, UnderlyingAsset
from ..security import Symbol, SecurityType


class Swap(Derivative):
    """
    Base Swap entity.
    No leg notionals or rates (these go to a factor table).
    """

    def __init__(self,
                 id: int,
                 underlying_asset: FinancialAsset,
                 effective_date: date,
                 maturity_date: date,
                 start_date: date,
                 end_date: Optional[date] = None):
        
        super().__init__(id, underlying_asset, start_date, end_date)
        
        self.effective_date = effective_date
        self.maturity_date = maturity_date
