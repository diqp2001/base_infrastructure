from __future__ import annotations

from enum import Enum
from typing import Optional
from datetime import datetime

from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset

class PositionType(Enum):
    """Type of position for an option leg."""
    LONG = "LONG"
    SHORT = "SHORT"

class Position:
    """
    .
    """

    def __init__(
        self,
        id: int,
        quantity: int,
        position_type: PositionType,
        
    ):
        self.id = id
        self.quantity = quantity
        self.position_type = position_type

    
