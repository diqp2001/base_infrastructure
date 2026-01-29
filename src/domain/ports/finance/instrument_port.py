"""
Instrument Port - Repository interface for Instrument entities.

This port defines the contract for repositories that handle Instrument
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime

from src.domain.entities.finance.instrument.instrument import Instrument


class InstrumentPort(ABC):
    """Port interface for Instrument repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[Instrument]:
        """
        Get instrument by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            Instrument entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_asset_id(self, asset_id: int) -> List[Instrument]:
        """
        Get instruments by asset ID.
        
        Args:
            asset_id: The financial asset ID
            
        Returns:
            List of Instrument entities for the asset
        """
        pass
    
    @abstractmethod
    def get_by_source(self, source: str) -> List[Instrument]:
        """
        Get instruments by data source.
        
        Args:
            source: The data source name
            
        Returns:
            List of Instrument entities from the source
        """
        pass
    
    @abstractmethod
    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Instrument]:
        """
        Get instruments within a date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of Instrument entities within the date range
        """
        pass
    
    @abstractmethod
    def get_by_asset_and_source(self, asset_id: int, source: str) -> List[Instrument]:
        """
        Get instruments by asset ID and source.
        
        Args:
            asset_id: The financial asset ID
            source: The data source name
            
        Returns:
            List of Instrument entities matching both criteria
        """
        pass
    
    @abstractmethod
    def get_latest_by_asset(self, asset_id: int) -> Optional[Instrument]:
        """
        Get the most recent instrument for an asset.
        
        Args:
            asset_id: The financial asset ID
            
        Returns:
            Most recent Instrument entity for the asset or None if not found
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[Instrument]:
        """
        Get all instruments.
        
        Returns:
            List of all Instrument entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: Instrument) -> Optional[Instrument]:
        """
        Add/persist an instrument entity.
        
        Args:
            entity: The Instrument entity to persist
            
        Returns:
            Persisted Instrument entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: Instrument) -> Optional[Instrument]:
        """
        Update an instrument entity.
        
        Args:
            entity: The Instrument entity to update
            
        Returns:
            Updated Instrument entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete an instrument entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def count_by_source(self, source: str) -> int:
        """
        Count instruments by source.
        
        Args:
            source: The data source name
            
        Returns:
            Number of instruments from the source
        """
        pass
    
    @abstractmethod
    def get_unique_sources(self) -> List[str]:
        """
        Get list of unique data sources.
        
        Returns:
            List of unique source names
        """
        pass