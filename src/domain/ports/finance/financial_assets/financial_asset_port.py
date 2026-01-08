from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class FinancialAssetPort(ABC):
    """Port interface for FinancialAsset entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, asset_id: int) -> Optional[FinancialAsset]:
        """Retrieve a financial asset by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[FinancialAsset]:
        """Retrieve all financial assets."""
        pass
    
    @abstractmethod
    def get_active_assets(self) -> List[FinancialAsset]:
        """Retrieve all active financial assets (end_date is None or in the future)."""
        pass
    
    @abstractmethod
    def get_by_asset_type(self, asset_type: str) -> List[FinancialAsset]:
        """Retrieve financial assets by their asset type."""
        pass
    
    @abstractmethod
    def add(self, asset: FinancialAsset) -> FinancialAsset:
        """Add a new financial asset."""
        pass
    
    @abstractmethod
    def update(self, asset: FinancialAsset) -> FinancialAsset:
        """Update an existing financial asset."""
        pass
    
    @abstractmethod
    def delete(self, asset_id: int) -> bool:
        """Delete a financial asset by its ID."""
        pass