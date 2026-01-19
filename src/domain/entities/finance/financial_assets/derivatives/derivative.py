"""
Derivatives base class for derivative financial instruments.
Parent class for Options, Futures, Swaps, and Forward Contracts.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass

from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset





class Derivative(FinancialAsset):
    """
    Base class for all derivatives.
    Stores only identification info and links to underlying assets.
    """
    def __init__(
            self,
            id: Optional[int],
            name: Optional[str],
            symbol: Optional[str],
            underlying_asset: FinancialAsset,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
        ):

        super().__init__(id, name, symbol, start_date, end_date)
    
        self.underlying_asset = underlying_asset  # <— ANY child of FinancialAsset

    
