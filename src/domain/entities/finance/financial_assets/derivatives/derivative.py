"""
Derivatives base class for derivative financial instruments.
Parent class for Options, Futures, Swaps, and Forward Contracts.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass

from domain.entities.finance.financial_assets.financial_asset import FinancialAsset
from ..security import Security, Symbol, SecurityType, MarketData


@dataclass
class UnderlyingAsset:
    """Value object representing the underlying asset."""
    symbol: str
    asset_type: str  # "STOCK", "INDEX", "COMMODITY", "BOND", "CRYPTO"
    current_price: Optional[Decimal] = None
    
    def __post_init__(self):
        if self.current_price is not None and self.current_price < 0:
            raise ValueError("Current price cannot be negative")


class Derivative(FinancialAsset):
    """
    Base class for all derivatives.
    Stores only identification info and links to underlying assets.
    """

    def __init__(self,
                 id: int,
                 underlying_asset: FinancialAsset,
                 start_date: date,
                 end_date: Optional[date]):
        
        super().__init__(id, start_date, end_date)
        self.underlying_asset = underlying_asset  # <— ANY child of FinancialAsset

    
    def __repr__(self) -> str:
        return (f"Derivative(symbol={self.symbol.ticker}, "
                f"underlying={self.underlying_asset.symbol}, "
                f"price=${self.price}, expiry={self.expiration_date})")