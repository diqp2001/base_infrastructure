from __future__ import annotations

from typing import Optional
from datetime import datetime

from src.domain.entities.entity import Entity
from src.domain.entities.finance.holding.position import Position
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class Holding(Entity):
    """
    Base class representing an asset held inside a container
    (portfolio, book, strategy, account).
    """

    def __init__(
        self,
        id: Optional[int],
        asset: FinancialAsset,
        container: object,
        position: Position,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ):
        super().__init__(id)
        self.asset = asset
        self.container = container
        self.position = position
        self.start_date = start_date
        self.end_date = end_date

    def is_active(self) -> bool:
        if self.end_date and datetime.now() > self.end_date:
            return False
        return True

    def __repr__(self) -> str:
        return f"Holding(id={self.id}, asset={self.asset})"
