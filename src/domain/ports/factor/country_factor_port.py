"""
Country Factor Port - Repository interface for CountryFactor entities.

This port defines the contract for repositories that handle CountryFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.country_factor import CountryFactor


class CountryFactorPort(ABC):
    """Port interface for CountryFactor repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[CountryFactor]:
        """
        Get country factor by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            CountryFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CountryFactor]:
        """
        Get country factor by name.
        
        Args:
            name: The factor name
            
        Returns:
            CountryFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_country_code(self, country_code: str) -> List[CountryFactor]:
        """
        Get country factors by country code.
        
        Args:
            country_code: The country code (e.g., 'US', 'CA')
            
        Returns:
            List of CountryFactor entities for the country
        """
        pass
    
    @abstractmethod
    def get_by_currency(self, currency: str) -> List[CountryFactor]:
        """
        Get country factors by currency.
        
        Args:
            currency: The currency code (e.g., 'USD', 'EUR')
            
        Returns:
            List of CountryFactor entities with the currency
        """
        pass
    
    @abstractmethod
    def get_by_development_status(self, is_developed: bool) -> List[CountryFactor]:
        """
        Get country factors by development status.
        
        Args:
            is_developed: Whether the country is developed
            
        Returns:
            List of CountryFactor entities with the development status
        """
        pass
    
    @abstractmethod
    def get_by_group(self, group: str) -> List[CountryFactor]:
        """
        Get country factors by group.
        
        Args:
            group: The factor group
            
        Returns:
            List of CountryFactor entities in the group
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[CountryFactor]:
        """
        Get all country factors.
        
        Returns:
            List of CountryFactor entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: CountryFactor) -> Optional[CountryFactor]:
        """
        Add/persist a country factor entity.
        
        Args:
            entity: The CountryFactor entity to persist
            
        Returns:
            Persisted CountryFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: CountryFactor) -> Optional[CountryFactor]:
        """
        Update a country factor entity.
        
        Args:
            entity: The CountryFactor entity to update
            
        Returns:
            Updated CountryFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a country factor entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass