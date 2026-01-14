from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.crypto import Crypto


class CryptoPort(ABC):
    """Port interface for Crypto entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, crypto_id: int) -> Optional[Crypto]:
    #     """Retrieve a crypto entity by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Crypto]:
    #     """Retrieve all crypto entities."""
    #     pass
    
    # @abstractmethod
    # def get_active_cryptos(self) -> List[Crypto]:
    #     """Retrieve all active crypto entities (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, crypto: Crypto) -> Crypto:
    #     """Add a new crypto entity."""
    #     pass
    
    # @abstractmethod
    # def update(self, crypto: Crypto) -> Crypto:
    #     """Update an existing crypto entity."""
    #     pass
    
    # @abstractmethod
    # def delete(self, crypto_id: int) -> bool:
    #     """Delete a crypto entity by its ID."""
    #     pass