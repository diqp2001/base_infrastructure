from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.time_series.dask_time_series import DaskTimeSeries
import pandas as pd
import dask.dataframe as dd


class DaskTimeSeriesPort(ABC):
    """Port interface for DaskTimeSeries entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, time_series_id: str) -> Optional[DaskTimeSeries]:
        """Retrieve a Dask time series by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[DaskTimeSeries]:
        """Retrieve all Dask time series."""
        pass
    
    @abstractmethod
    def get_by_columns(self, columns: List[str]) -> List[DaskTimeSeries]:
        """Retrieve Dask time series containing specific columns."""
        pass
    
    @abstractmethod
    def get_by_date_range(self, start_date: pd.Timestamp, end_date: pd.Timestamp) -> List[DaskTimeSeries]:
        """Retrieve Dask time series within a date range."""
        pass
    
    @abstractmethod
    def save_time_series(self, time_series_id: str, time_series: DaskTimeSeries) -> DaskTimeSeries:
        """Save a Dask time series with the given ID."""
        pass
    
    @abstractmethod
    def update_time_series(self, time_series_id: str, time_series: DaskTimeSeries) -> DaskTimeSeries:
        """Update an existing Dask time series."""
        pass
    
    @abstractmethod
    def delete(self, time_series_id: str) -> bool:
        """Delete a Dask time series by its ID."""
        pass
    
    @abstractmethod
    def persist_to_storage(self, time_series: DaskTimeSeries, path: str) -> bool:
        """Persist a Dask time series to storage (e.g., Parquet format)."""
        pass