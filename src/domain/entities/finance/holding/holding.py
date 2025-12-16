from __future__ import annotations

from typing import Optional
from datetime import datetime

from domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class Holding:
    """
    Base class representing an asset held inside a container
    (portfolio, book, strategy, account).

    Identification-only.
    """

    def __init__(
        self,
        id: int,
        asset: FinancialAsset,
        container: object,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ):
        self.id = id
        self.asset = asset
        self.container = container
        self.start_date = start_date
        self.end_date = end_date

    def is_active(self) -> bool:
        if self.end_date and datetime.now() > self.end_date:
            return False
        return True
