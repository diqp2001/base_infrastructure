"""
Company Port - Repository interface for Company entities.

This port defines the contract for repositories that handle Company
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import date

from src.domain.entities.finance.company import Company


class CompanyPort(ABC):
    """Port interface for Company repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[Company]:
        """
        Get company by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            Company entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Company]:
        """
        Get company by name.
        
        Args:
            name: The company name
            
        Returns:
            Company entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_legal_name(self, legal_name: str) -> Optional[Company]:
        """
        Get company by legal name.
        
        Args:
            legal_name: The company legal name
            
        Returns:
            Company entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_country_id(self, country_id: int) -> List[Company]:
        """
        Get companies by country ID.
        
        Args:
            country_id: The country ID
            
        Returns:
            List of Company entities in the country
        """
        pass
    
    @abstractmethod
    def get_by_industry_id(self, industry_id: int) -> List[Company]:
        """
        Get companies by industry ID.
        
        Args:
            industry_id: The industry ID
            
        Returns:
            List of Company entities in the industry
        """
        pass
    
    @abstractmethod
    def get_active_companies(self, as_of_date: Optional[date] = None) -> List[Company]:
        """
        Get active companies as of a specific date.
        
        Args:
            as_of_date: Date to check activity (defaults to today)
            
        Returns:
            List of active Company entities
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[Company]:
        """
        Get all companies.
        
        Returns:
            List of Company entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: Company) -> Optional[Company]:
        """
        Add/persist a company entity.
        
        Args:
            entity: The Company entity to persist
            
        Returns:
            Persisted Company entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: Company) -> Optional[Company]:
        """
        Update a company entity.
        
        Args:
            entity: The Company entity to update
            
        Returns:
            Updated Company entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a company entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass