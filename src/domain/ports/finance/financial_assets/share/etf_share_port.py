from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.share.etf_share import ETFShare


class ETFSharePort(ABC):
    """Port interface for ETFShare entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, etf_share_id: int) -> Optional[ETFShare]:
    #     """Retrieve an ETF share by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[ETFShare]:
    #     """Retrieve all ETF shares."""
    #     pass
    
    # @abstractmethod
    # def get_by_exchange_id(self, exchange_id: int) -> List[ETFShare]:
    #     """Retrieve ETF shares by exchange ID."""
    #     pass
    
    # @abstractmethod
    # def get_active_etf_shares(self) -> List[ETFShare]:
    #     """Retrieve all active ETF shares (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, etf_share: ETFShare) -> ETFShare:
    #     """Add a new ETF share."""
    #     pass
    
    # @abstractmethod
    # def update(self, etf_share: ETFShare) -> ETFShare:
    #     """Update an existing ETF share."""
    #     pass
    
    # @abstractmethod
    # def delete(self, etf_share_id: int) -> bool:
    #     """Delete an ETF share by its ID."""
    #     pass