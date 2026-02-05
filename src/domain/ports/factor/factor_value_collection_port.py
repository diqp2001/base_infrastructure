"""
Factor Value Collection Port - Repository interface for FactorValueCollection entities.

This port defines the contract for repositories that handle FactorValueCollection
entities, ensuring consistent access patterns for batch factor value operations.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime

from src.domain.entities.factor.factor_value_collection import FactorValueCollection


class FactorValueCollectionPort(ABC):
    """Port interface for FactorValueCollection repositories"""
    
    @abstractmethod
    def create_from_factor_value_list(self, factor_value_list: List) -> Optional[FactorValueCollection]:
        """
        Create a FactorValueCollection from a list of factor values.
        
        Args:
            factor_value_list: List of FactorValue entities
            
        Returns:
            FactorValueCollection entity or None if creation failed
        """
        pass
    
    @abstractmethod
    def bulk_save_to_database(self, collection: FactorValueCollection) -> bool:
        """
        Bulk save all factor values in the collection to the database.
        
        Args:
            collection: FactorValueCollection to save
            
        Returns:
            True if all factor values were saved successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_values_by_factor_id(self, factor_id: int) -> Optional[FactorValueCollection]:
        """
        Get all factor values for a factor ID as a FactorValueCollection.
        
        Args:
            factor_id: The factor ID
            
        Returns:
            FactorValueCollection containing factor values or None
        """
        pass
    
    @abstractmethod
    def get_values_by_entity_id(self, entity_id: int) -> Optional[FactorValueCollection]:
        """
        Get all factor values for an entity ID as a FactorValueCollection.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            FactorValueCollection containing factor values or None
        """
        pass
    
    @abstractmethod
    def get_values_by_date_range(self, start_date: datetime, end_date: datetime) -> Optional[FactorValueCollection]:
        """
        Get all factor values within a date range as a FactorValueCollection.
        
        Args:
            start_date: Start date for the range
            end_date: End date for the range
            
        Returns:
            FactorValueCollection containing factor values in date range or None
        """
        pass
    
    @abstractmethod
    def get_values_by_composite_filter(self, factor_ids: List[int], entity_ids: List[int], 
                                     start_date: datetime, end_date: datetime) -> Optional[FactorValueCollection]:
        """
        Get factor values by multiple criteria as a FactorValueCollection.
        
        Args:
            factor_ids: List of factor IDs to include
            entity_ids: List of entity IDs to include
            start_date: Start date for the range
            end_date: End date for the range
            
        Returns:
            FactorValueCollection containing filtered factor values or None
        """
        pass
    
    @abstractmethod
    def prepare_batch_insert(self, collection: FactorValueCollection) -> List[dict]:
        """
        Prepare factor values for efficient batch database insertion.
        
        Args:
            collection: FactorValueCollection to prepare
            
        Returns:
            List of dictionaries ready for batch insertion
        """
        pass