from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.derivatives.option.option import Option


class OptionPort(ABC):
    """Port interface for Option entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, option_id: int) -> Optional[Option]:
    #     """Retrieve an option by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Option]:
    #     """Retrieve all options."""
    #     pass
    
    # @abstractmethod
    # def get_by_strike_price(self, strike_price: float) -> List[Option]:
    #     """Retrieve options by their strike price."""
    #     pass
    
    # @abstractmethod
    # def get_by_expiration_date(self, expiration_date: str) -> List[Option]:
    #     """Retrieve options by their expiration date."""
    #     pass
    
    # @abstractmethod
    # def get_by_option_type(self, option_type: str) -> List[Option]:
    #     """Retrieve options by their type (call or put)."""
    #     pass
    
    # @abstractmethod
    # def get_active_options(self) -> List[Option]:
    #     """Retrieve all active options (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, option: Option) -> Option:
    #     """Add a new option."""
    #     pass
    
    # @abstractmethod
    # def update(self, option: Option) -> Option:
    #     """Update an existing option."""
    #     pass
    
    # @abstractmethod
    # def delete(self, option_id: int) -> bool:
    #     """Delete an option by its ID."""
    #     pass