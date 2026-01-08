from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.time_series.finance.financial_asset_time_series import FinancialAssetTimeSeries
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset
import pandas as pd


class FinancialAssetTimeSeriesPort(ABC):
    """Port interface for FinancialAssetTimeSeries entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, time_series_id: str) -> Optional[FinancialAssetTimeSeries]:
        """Retrieve a financial asset time series by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[FinancialAssetTimeSeries]:
        """Retrieve all financial asset time series."""
        pass
    
    @abstractmethod
    def get_by_asset(self, asset: FinancialAsset) -> List[FinancialAssetTimeSeries]:
        """Retrieve time series by financial asset."""
        pass
    
    @abstractmethod
    def get_by_date_range(self, start_date: pd.Timestamp, end_date: pd.Timestamp) -> List[FinancialAssetTimeSeries]:
        """Retrieve financial asset time series within a date range."""
        pass
    
    @abstractmethod
    def get_by_columns(self, columns: List[str]) -> List[FinancialAssetTimeSeries]:
        """Retrieve financial asset time series containing specific columns (e.g., OHLCV)."""
        pass
    
    @abstractmethod
    def save_time_series(self, time_series_id: str, time_series: FinancialAssetTimeSeries) -> FinancialAssetTimeSeries:
        """Save a financial asset time series with the given ID."""
        pass
    
    @abstractmethod
    def update_time_series(self, time_series_id: str, time_series: FinancialAssetTimeSeries) -> FinancialAssetTimeSeries:
        """Update an existing financial asset time series."""
        pass
    
    @abstractmethod
    def delete(self, time_series_id: str) -> bool:
        """Delete a financial asset time series by its ID."""
        pass