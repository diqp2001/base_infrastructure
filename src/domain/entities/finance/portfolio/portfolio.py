from __future__ import annotations

from datetime import date
from typing import List, Optional

from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset



class Portfolio():
    """
    Pure identification Portfolio.

    Represents a basket / collection of underlying financial assets.
    Allocation, weights, risk, PnL, etc. live elsewhere (factors/services).
    """

    def __init__(
        self,
        id: int,
        name: str,
        start_date: date,
        end_date: Optional[date] = None,
    ):
        
        self.id = id
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
