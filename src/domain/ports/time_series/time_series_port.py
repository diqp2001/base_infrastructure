"""
Time Series Port - Repository interface for TimeSeries entities.

This port defines the contract for repositories that handle TimeSeries
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
import pandas as pd

from src.domain.entities.time_series.time_series import TimeSeries


class TimeSeriesPort(ABC):
    """Port interface for TimeSeries repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[TimeSeries]:
        """
        Get time series by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            TimeSeries entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[TimeSeries]:
        """
        Get time series by name.
        
        Args:
            name: The time series name
            
        Returns:
            TimeSeries entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_date_range(self, start_date, end_date) -> List[TimeSeries]:
        """
        Get time series within date range.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of TimeSeries entities within the date range
        """
        pass
    
    @abstractmethod
    def get_by_columns(self, columns: List[str]) -> List[TimeSeries]:
        """
        Get time series containing specific columns.
        
        Args:
            columns: List of column names to search for
            
        Returns:
            List of TimeSeries entities containing the columns
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[TimeSeries]:
        """
        Get all time series.
        
        Returns:
            List of TimeSeries entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: TimeSeries) -> Optional[TimeSeries]:
        """
        Add/persist a time series entity.
        
        Args:
            entity: The TimeSeries entity to persist
            
        Returns:
            Persisted TimeSeries entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: TimeSeries) -> Optional[TimeSeries]:
        """
        Update a time series entity.
        
        Args:
            entity: The TimeSeries entity to update
            
        Returns:
            Updated TimeSeries entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a time series entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def save_dataframe(self, dataframe: pd.DataFrame, name: str) -> Optional[TimeSeries]:
        """
        Save a pandas DataFrame as a TimeSeries entity.
        
        Args:
            dataframe: The DataFrame to save
            name: Name for the time series
            
        Returns:
            Created TimeSeries entity or None if failed
        """
        pass