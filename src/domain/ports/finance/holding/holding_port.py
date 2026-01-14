from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.holding.holding import Holding
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class HoldingPort(ABC):
    """Port interface for Holding entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, holding_id: int) -> Optional[Holding]:
    #     """Retrieve a holding by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Holding]:
    #     """Retrieve all holdings."""
    #     pass
    
    # @abstractmethod
    # def get_by_asset(self, asset: FinancialAsset) -> List[Holding]:
    #     """Retrieve holdings by asset."""
    #     pass
    
    # @abstractmethod
    # def get_by_container(self, container: object) -> List[Holding]:
    #     """Retrieve holdings by container (portfolio, book, strategy, account)."""
    #     pass
    
    # @abstractmethod
    # def get_active_holdings(self) -> List[Holding]:
    #     """Retrieve all active holdings (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, holding: Holding) -> Holding:
    #     """Add a new holding."""
    #     pass
    
    # @abstractmethod
    # def update(self, holding: Holding) -> Holding:
    #     """Update an existing holding."""
    #     pass
    
    # @abstractmethod
    # def delete(self, holding_id: int) -> bool:
    #     """Delete a holding by its ID."""
    #     pass