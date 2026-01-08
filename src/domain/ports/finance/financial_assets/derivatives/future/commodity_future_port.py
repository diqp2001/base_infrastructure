from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.derivatives.future.commodity_future import CommodityFuture


class CommodityFuturePort(ABC):
    """Port interface for CommodityFuture entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, future_id: int) -> Optional[CommodityFuture]:
        """Retrieve a commodity future by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[CommodityFuture]:
        """Retrieve all commodity futures."""
        pass
    
    @abstractmethod
    def get_by_commodity_type(self, commodity_type: str) -> List[CommodityFuture]:
        """Retrieve commodity futures by their underlying commodity type."""
        pass
    
    @abstractmethod
    def get_by_delivery_location(self, delivery_location: str) -> List[CommodityFuture]:
        """Retrieve commodity futures by their delivery location."""
        pass
    
    @abstractmethod
    def get_by_quality_grade(self, quality_grade: str) -> List[CommodityFuture]:
        """Retrieve commodity futures by their quality grade."""
        pass
    
    @abstractmethod
    def get_active_futures(self) -> List[CommodityFuture]:
        """Retrieve all active commodity futures (end_date is None or in the future)."""
        pass
    
    @abstractmethod
    def add(self, future: CommodityFuture) -> CommodityFuture:
        """Add a new commodity future."""
        pass
    
    @abstractmethod
    def update(self, future: CommodityFuture) -> CommodityFuture:
        """Update an existing commodity future."""
        pass
    
    @abstractmethod
    def delete(self, future_id: int) -> bool:
        """Delete a commodity future by its ID."""
        pass