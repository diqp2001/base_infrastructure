from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.finance.financial_assets.share.etf_share.etf_share import ETFShare


class ETFSharePort(ABC):
    """Port interface for ETFShare entity operations following repository pattern."""

    @abstractmethod
    def get_by_id(self, etf_share_id: int) -> Optional[ETFShare]:
        """Retrieve an ETF share by its ID."""

    @abstractmethod
    def get_by_symbol(self, symbol: str) -> Optional[ETFShare]:
        """Retrieve an ETF share by its ticker."""

    @abstractmethod
    def get_all(self) -> List[ETFShare]:
        """Retrieve all ETF shares."""

    @abstractmethod
    def add(self, etf_share: ETFShare) -> ETFShare:
        """Add a new ETF share (the existing one when the ticker is already stored)."""
