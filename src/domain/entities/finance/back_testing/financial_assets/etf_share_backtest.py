"""
ETF Share backtest class extending ShareBackTest with ETF-specific functionality.
Provides NAV tracking, creation/redemption features, and basket composition.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict
from src.domain.entities.finance.back_testing.financial_assets.share_backtest import ShareBackTest
from src.domain.entities.finance.back_testing.financial_assets.symbol import Symbol
from src.domain.entities.finance.back_testing.enums import SecurityType


@dataclass
class NAVCalculation:
    """Value object for Net Asset Value calculations."""
    nav_per_share: Decimal
    total_net_assets: Decimal
    shares_outstanding: Decimal
    calculation_date: datetime
    
    def __post_init__(self):
        if self.nav_per_share < 0:
            raise ValueError("NAV per share cannot be negative")
        if self.shares_outstanding <= 0:
            raise ValueError("Shares outstanding must be positive")


@dataclass
class BasketHolding:
    """Value object for ETF basket holdings."""
    symbol: str
    quantity: Decimal
    market_value: Decimal
    weight_percentage: Decimal
    last_updated: datetime
    
    def __post_init__(self):
        if self.quantity < 0:
            raise ValueError("Quantity cannot be negative")
        if self.weight_percentage < 0 or self.weight_percentage > 100:
            raise ValueError("Weight percentage must be between 0 and 100")


@dataclass
class CreationRedemption:
    """Value object for creation/redemption events."""
    event_type: str  # "creation" or "redemption"
    shares_amount: Decimal
    nav_price: Decimal
    event_date: datetime
    authorized_participant: str
    
    def __post_init__(self):
        if self.event_type not in ["creation", "redemption"]:
            raise ValueError("Event type must be 'creation' or 'redemption'")
        if self.shares_amount <= 0:
            raise ValueError("Shares amount must be positive")


