"""
Financial Asset Factor Port - Repository interface for FinancialAssetFactor entities.

This port defines the contract for repositories that handle FinancialAssetFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.financial_asset_factor import FinancialAssetFactor


class FinancialAssetFactorPort(ABC):
    """Port interface for FinancialAssetFactor repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[FinancialAssetFactor]:
        """
        Get financial asset factor by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            FinancialAssetFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[FinancialAssetFactor]:
        """
        Get financial asset factor by name.
        
        Args:
            name: The factor name
            
        Returns:
            FinancialAssetFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_asset_class(self, asset_class: str) -> List[FinancialAssetFactor]:
        """
        Get financial asset factors by asset class.
        
        Args:
            asset_class: The asset class (e.g., 'equity', 'bond', 'derivative', 'commodity')
            
        Returns:
            List of FinancialAssetFactor entities for the asset class
        """
        pass
    
    @abstractmethod
    def get_by_currency(self, currency: str) -> List[FinancialAssetFactor]:
        """
        Get financial asset factors by currency.
        
        Args:
            currency: The currency code (e.g., 'USD', 'EUR', 'GBP')
            
        Returns:
            List of FinancialAssetFactor entities denominated in the currency
        """
        pass
    
    @abstractmethod
    def get_by_risk_level(self, risk_level: str) -> List[FinancialAssetFactor]:
        """
        Get financial asset factors by risk level.
        
        Args:
            risk_level: The risk level (e.g., 'low', 'medium', 'high')
            
        Returns:
            List of FinancialAssetFactor entities with the specified risk level
        """
        pass
    
    @abstractmethod
    def get_by_liquidity_tier(self, tier: str) -> List[FinancialAssetFactor]:
        """
        Get financial asset factors by liquidity tier.
        
        Args:
            tier: The liquidity tier (e.g., 'tier1', 'tier2', 'illiquid')
            
        Returns:
            List of FinancialAssetFactor entities in the liquidity tier
        """
        pass
    
    @abstractmethod
    def get_by_group(self, group: str) -> List[FinancialAssetFactor]:
        """
        Get financial asset factors by group.
        
        Args:
            group: The factor group
            
        Returns:
            List of FinancialAssetFactor entities in the group
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[FinancialAssetFactor]:
        """
        Get all financial asset factors.
        
        Returns:
            List of FinancialAssetFactor entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: FinancialAssetFactor) -> Optional[FinancialAssetFactor]:
        """
        Add/persist a financial asset factor entity.
        
        Args:
            entity: The FinancialAssetFactor entity to persist
            
        Returns:
            Persisted FinancialAssetFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: FinancialAssetFactor) -> Optional[FinancialAssetFactor]:
        """
        Update a financial asset factor entity.
        
        Args:
            entity: The FinancialAssetFactor entity to update
            
        Returns:
            Updated FinancialAssetFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a financial asset factor entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass