"""
Bond Factor Port - Repository interface for BondFactor entities.

This port defines the contract for repositories that handle BondFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.bond_factor.bond_factor import BondFactor


class BondFactorPort(ABC):
    """Port interface for BondFactor repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[BondFactor]:
        """
        Get bond factor by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            BondFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[BondFactor]:
        """
        Get bond factor by name.
        
        Args:
            name: The factor name
            
        Returns:
            BondFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_bond_type(self, bond_type: str) -> List[BondFactor]:
        """
        Get bond factors by bond type.
        
        Args:
            bond_type: The bond type (e.g., 'corporate', 'government', 'municipal')
            
        Returns:
            List of BondFactor entities for the bond type
        """
        pass
    
    @abstractmethod
    def get_by_maturity_range(self, min_years: Optional[float] = None, max_years: Optional[float] = None) -> List[BondFactor]:
        """
        Get bond factors by maturity range.
        
        Args:
            min_years: Minimum maturity in years
            max_years: Maximum maturity in years
            
        Returns:
            List of BondFactor entities within the maturity range
        """
        pass
    
    @abstractmethod
    def get_by_credit_rating(self, rating: str) -> List[BondFactor]:
        """
        Get bond factors by credit rating.
        
        Args:
            rating: The credit rating (e.g., 'AAA', 'AA+', 'BBB-')
            
        Returns:
            List of BondFactor entities with the credit rating
        """
        pass
    
    @abstractmethod
    def get_by_group(self, group: str) -> List[BondFactor]:
        """
        Get bond factors by group.
        
        Args:
            group: The factor group
            
        Returns:
            List of BondFactor entities in the group
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[BondFactor]:
        """
        Get all bond factors.
        
        Returns:
            List of BondFactor entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: BondFactor) -> Optional[BondFactor]:
        """
        Add/persist a bond factor entity.
        
        Args:
            entity: The BondFactor entity to persist
            
        Returns:
            Persisted BondFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: BondFactor) -> Optional[BondFactor]:
        """
        Update a bond factor entity.
        
        Args:
            entity: The BondFactor entity to update
            
        Returns:
            Updated BondFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a bond factor entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass