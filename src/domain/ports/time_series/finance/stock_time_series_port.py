from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.time_series.finance.stock_time_series import StockTimeSeries
from src.domain.entities.finance.financial_assets.stock import Stock
import pandas as pd


class StockTimeSeriesPort(ABC):
    """Port interface for StockTimeSeries entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, time_series_id: str) -> Optional[StockTimeSeries]:
        """Retrieve a stock time series by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[StockTimeSeries]:
        """Retrieve all stock time series."""
        pass
    
    @abstractmethod
    def get_by_stock(self, stock: Stock) -> List[StockTimeSeries]:
        """Retrieve time series by stock."""
        pass
    
    @abstractmethod
    def get_by_sector(self, sector: str) -> List[StockTimeSeries]:
        """Retrieve stock time series by sector."""
        pass
    
    @abstractmethod
    def get_by_country(self, country: str) -> List[StockTimeSeries]:
        """Retrieve stock time series by country."""
        pass
    
    @abstractmethod
    def get_by_date_range(self, start_date: pd.Timestamp, end_date: pd.Timestamp) -> List[StockTimeSeries]:
        """Retrieve stock time series within a date range."""
        pass
    
    @abstractmethod
    def save_time_series(self, time_series_id: str, time_series: StockTimeSeries) -> StockTimeSeries:
        """Save a stock time series with the given ID."""
        pass
    
    @abstractmethod
    def update_time_series(self, time_series_id: str, time_series: StockTimeSeries) -> StockTimeSeries:
        """Update an existing stock time series."""
        pass
    
    @abstractmethod
    def delete(self, time_series_id: str) -> bool:
        """Delete a stock time series by its ID."""
        pass