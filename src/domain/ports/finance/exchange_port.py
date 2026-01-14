from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.exchange import Exchange


class ExchangePort(ABC):
    """Port interface for Exchange entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, exchange_id: int) -> Optional[Exchange]:
    #     """Retrieve an exchange by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Exchange]:
    #     """Retrieve all exchanges."""
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[Exchange]:
    #     """Retrieve an exchange by its name."""
    #     pass
    
    # @abstractmethod
    # def get_by_country_id(self, country_id: int) -> List[Exchange]:
    #     """Retrieve exchanges by country ID."""
    #     pass
    
    # @abstractmethod
    # def get_active_exchanges(self) -> List[Exchange]:
    #     """Retrieve all active exchanges (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, exchange: Exchange) -> Exchange:
    #     """Add a new exchange."""
    #     pass
    
    # @abstractmethod
    # def update(self, exchange: Exchange) -> Exchange:
    #     """Update an existing exchange."""
    #     pass
    
    # @abstractmethod
    # def delete(self, exchange_id: int) -> bool:
    #     """Delete an exchange by its ID."""
    #     pass