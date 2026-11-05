from abc import ABC, abstractmethod
from typing import List

from src.domain.entities.finance.financial_assets.derivatives.option.etf_share_option import ETFShareOption


class ETFShareOptionPort(ABC):
    """Port interface for ETFShareOption entity operations following repository pattern."""

    @abstractmethod
    def get_by_underlying_id(self, underlying_asset_id: int) -> List[ETFShareOption]:
        """Retrieve the options written on one ETF share."""

    @abstractmethod
    def add(self, option: ETFShareOption) -> ETFShareOption:
        """Add a new ETF share option."""
