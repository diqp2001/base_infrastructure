from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from src.domain.entities.time_series.ml.ml_time_series import MlTimeSeries
import pandas as pd


class MlTimeSeriesPort(ABC):
    """Port interface for MlTimeSeries entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, time_series_id: str) -> Optional[MlTimeSeries]:
        """Retrieve an ML time series by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[MlTimeSeries]:
        """Retrieve all ML time series."""
        pass
    
    @abstractmethod
    def get_by_target_column(self, y_column: str) -> List[MlTimeSeries]:
        """Retrieve ML time series by target column."""
        pass
    
    @abstractmethod
    def get_by_features(self, x_columns: List[str]) -> List[MlTimeSeries]:
        """Retrieve ML time series containing specific feature columns."""
        pass
    
    @abstractmethod
    def get_split_data(self, time_series_id: str) -> Optional[Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]]:
        """Retrieve train/test split data for an ML time series (train_x, train_y, test_x, test_y)."""
        pass
    
    @abstractmethod
    def save_time_series(self, time_series_id: str, time_series: MlTimeSeries) -> MlTimeSeries:
        """Save an ML time series with the given ID."""
        pass
    
    @abstractmethod
    def update_time_series(self, time_series_id: str, time_series: MlTimeSeries) -> MlTimeSeries:
        """Update an existing ML time series."""
        pass
    
    @abstractmethod
    def delete(self, time_series_id: str) -> bool:
        """Delete an ML time series by its ID."""
        pass
    
    @abstractmethod
    def save_model_results(self, time_series_id: str, model_name: str, predictions: pd.Series, metrics: dict) -> bool:
        """Save model predictions and metrics for an ML time series."""
        pass