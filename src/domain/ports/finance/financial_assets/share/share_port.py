from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.share.share import Share


class SharePort(ABC):
    """Port interface for Share entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, share_id: int) -> Optional[Share]:
    #     """Retrieve a share by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Share]:
    #     """Retrieve all shares."""
    #     pass
    
    # @abstractmethod
    # def get_by_exchange_id(self, exchange_id: int) -> List[Share]:
    #     """Retrieve shares by exchange ID."""
    #     pass
    
    # @abstractmethod
    # def get_active_shares(self) -> List[Share]:
    #     """Retrieve all active shares (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, share: Share) -> Share:
    #     """Add a new share."""
    #     pass
    
    # @abstractmethod
    # def update(self, share: Share) -> Share:
    #     """Update an existing share."""
    #     pass
    
    # @abstractmethod
    # def delete(self, share_id: int) -> bool:
    #     """Delete a share by its ID."""
    #     pass