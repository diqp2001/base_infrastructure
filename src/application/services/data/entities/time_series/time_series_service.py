"""
Time Series Service - handles creation and management of time series entities.
Provides a service layer for creating time series domain entities like TimeSeries, FinancialAssetTimeSeries, etc.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime
import pandas as pd

from src.domain.entities.time_series.time_series import TimeSeries
from src.domain.entities.time_series.dask_time_series import DaskTimeSeries
from src.domain.entities.time_series.finance.stock_time_series import StockTimeSeries
from src.domain.entities.time_series.finance.financial_asset_time_series import FinancialAssetTimeSeries
from src.domain.entities.time_series.ml.ml_time_series import MLTimeSeries


class TimeSeriesService:
    """Service for creating and managing time series domain entities."""
    
    def __init__(self, db_type: str = 'sqlite'):
        """Initialize the service with a database type."""
        self.db_type = db_type
    
    def create_time_series(
        self,
        name: str,
        frequency: str = 'D',  # Daily by default
        start_date: date = None,
        end_date: date = None,
        data: Union[pd.DataFrame, List[Dict]] = None,
        metadata: Dict[str, Any] = None
    ) -> TimeSeries:
        """Create a base TimeSeries entity."""
        return TimeSeries(
            name=name,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            data=data,
            metadata=metadata or {}
        )
    
    def create_dask_time_series(
        self,
        name: str,
        frequency: str = 'D',
        start_date: date = None,
        end_date: date = None,
        data: Union[pd.DataFrame, List[Dict]] = None,
        metadata: Dict[str, Any] = None,
        partitions: int = None,
        chunk_size: str = None
    ) -> DaskTimeSeries:
        """Create a DaskTimeSeries entity for large datasets."""
        return DaskTimeSeries(
            name=name,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            data=data,
            metadata=metadata or {},
            partitions=partitions,
            chunk_size=chunk_size
        )
    
    def create_stock_time_series(
        self,
        symbol: str,
        name: str = None,
        exchange: str = None,
        currency: str = "USD",
        frequency: str = 'D',
        start_date: date = None,
        end_date: date = None,
        data: Union[pd.DataFrame, List[Dict]] = None,
        metadata: Dict[str, Any] = None,
        adjusted_prices: bool = True,
        dividend_adjusted: bool = True,
        split_adjusted: bool = True
    ) -> StockTimeSeries:
        """Create a StockTimeSeries entity."""
        return StockTimeSeries(
            symbol=symbol,
            name=name or f"{symbol} Stock Data",
            exchange=exchange,
            currency=currency,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            data=data,
            metadata=metadata or {},
            adjusted_prices=adjusted_prices,
            dividend_adjusted=dividend_adjusted,
            split_adjusted=split_adjusted
        )
    
    def create_financial_asset_time_series(
        self,
        asset_id: str,
        asset_type: str,
        name: str = None,
        frequency: str = 'D',
        start_date: date = None,
        end_date: date = None,
        data: Union[pd.DataFrame, List[Dict]] = None,
        metadata: Dict[str, Any] = None,
        data_fields: List[str] = None
    ) -> FinancialAssetTimeSeries:
        """Create a FinancialAssetTimeSeries entity."""
        return FinancialAssetTimeSeries(
            asset_id=asset_id,
            asset_type=asset_type,
            name=name or f"{asset_id} {asset_type} Data",
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            data=data,
            metadata=metadata or {},
            data_fields=data_fields or ['open', 'high', 'low', 'close', 'volume']
        )
    
    def create_ml_time_series(
        self,
        name: str,
        target_variable: str,
        feature_columns: List[str] = None,
        frequency: str = 'D',
        start_date: date = None,
        end_date: date = None,
        data: Union[pd.DataFrame, List[Dict]] = None,
        metadata: Dict[str, Any] = None,
        model_type: str = None,
        prediction_horizon: int = 1
    ) -> MLTimeSeries:
        """Create an MLTimeSeries entity for machine learning purposes."""
        return MLTimeSeries(
            name=name,
            target_variable=target_variable,
            feature_columns=feature_columns or [],
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            data=data,
            metadata=metadata or {},
            model_type=model_type,
            prediction_horizon=prediction_horizon
        )
    
    # Factory methods from configuration
    def create_entity_from_config(self, series_type: str, config: Dict[str, Any]):
        """
        Create a time series entity from configuration based on series type.
        
        Args:
            series_type: Type of series ('time_series', 'stock', 'financial_asset', 'ml', 'dask')
            config: Configuration dictionary
            
        Returns:
            Time series entity instance
        """
        series_type = series_type.lower()
        
        if series_type == 'time_series':
            return self.create_time_series_from_config(config)
        elif series_type == 'dask_time_series' or series_type == 'dask':
            return self.create_dask_time_series_from_config(config)
        elif series_type == 'stock_time_series' or series_type == 'stock':
            return self.create_stock_time_series_from_config(config)
        elif series_type == 'financial_asset_time_series' or series_type == 'financial_asset':
            return self.create_financial_asset_time_series_from_config(config)
        elif series_type == 'ml_time_series' or series_type == 'ml':
            return self.create_ml_time_series_from_config(config)
        else:
            raise ValueError(f"Unsupported time series type: {series_type}")
    
    def create_time_series_from_config(self, config: Dict[str, Any]) -> TimeSeries:
        """Create a TimeSeries from configuration."""
        # Convert date strings to date objects if needed
        if 'start_date' in config and isinstance(config['start_date'], str):
            config['start_date'] = datetime.strptime(config['start_date'], '%Y-%m-%d').date()
        if 'end_date' in config and isinstance(config['end_date'], str):
            config['end_date'] = datetime.strptime(config['end_date'], '%Y-%m-%d').date()
        
        return self.create_time_series(**config)
    
    def create_dask_time_series_from_config(self, config: Dict[str, Any]) -> DaskTimeSeries:
        """Create a DaskTimeSeries from configuration."""
        # Convert date strings to date objects if needed
        if 'start_date' in config and isinstance(config['start_date'], str):
            config['start_date'] = datetime.strptime(config['start_date'], '%Y-%m-%d').date()
        if 'end_date' in config and isinstance(config['end_date'], str):
            config['end_date'] = datetime.strptime(config['end_date'], '%Y-%m-%d').date()
        
        return self.create_dask_time_series(**config)
    
    def create_stock_time_series_from_config(self, config: Dict[str, Any]) -> StockTimeSeries:
        """Create a StockTimeSeries from configuration."""
        # Convert date strings to date objects if needed
        if 'start_date' in config and isinstance(config['start_date'], str):
            config['start_date'] = datetime.strptime(config['start_date'], '%Y-%m-%d').date()
        if 'end_date' in config and isinstance(config['end_date'], str):
            config['end_date'] = datetime.strptime(config['end_date'], '%Y-%m-%d').date()
        
        return self.create_stock_time_series(**config)
    
    def create_financial_asset_time_series_from_config(self, config: Dict[str, Any]) -> FinancialAssetTimeSeries:
        """Create a FinancialAssetTimeSeries from configuration."""
        # Convert date strings to date objects if needed
        if 'start_date' in config and isinstance(config['start_date'], str):
            config['start_date'] = datetime.strptime(config['start_date'], '%Y-%m-%d').date()
        if 'end_date' in config and isinstance(config['end_date'], str):
            config['end_date'] = datetime.strptime(config['end_date'], '%Y-%m-%d').date()
        
        return self.create_financial_asset_time_series(**config)
    
    def create_ml_time_series_from_config(self, config: Dict[str, Any]) -> MLTimeSeries:
        """Create an MLTimeSeries from configuration."""
        # Convert date strings to date objects if needed
        if 'start_date' in config and isinstance(config['start_date'], str):
            config['start_date'] = datetime.strptime(config['start_date'], '%Y-%m-%d').date()
        if 'end_date' in config and isinstance(config['end_date'], str):
            config['end_date'] = datetime.strptime(config['end_date'], '%Y-%m-%d').date()
        
        return self.create_ml_time_series(**config)
    
    def validate_time_series_data(self, data: Union[pd.DataFrame, List[Dict]], frequency: str) -> List[str]:
        """
        Validate time series data format and consistency.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        if data is None:
            return errors  # Data is optional
        
        if isinstance(data, pd.DataFrame):
            if data.empty:
                errors.append("DataFrame is empty")
            elif not isinstance(data.index, pd.DatetimeIndex):
                errors.append("DataFrame must have a DatetimeIndex")
        elif isinstance(data, list):
            if not data:
                errors.append("Data list is empty")
            elif not all(isinstance(item, dict) for item in data):
                errors.append("Data list must contain dictionaries")
            elif not all('date' in item or 'datetime' in item for item in data):
                errors.append("Each data item must contain 'date' or 'datetime' field")
        else:
            errors.append("Data must be a pandas DataFrame or list of dictionaries")
        
        # Validate frequency
        valid_frequencies = ['D', 'H', 'M', 'Q', 'Y', 'W', 'B', 'min', 'S']
        if frequency not in valid_frequencies:
            errors.append(f"Frequency must be one of {valid_frequencies}")
        
        return errors
    
    def convert_data_format(self, data: Union[pd.DataFrame, List[Dict]], target_format: str = 'dataframe'):
        """
        Convert time series data between different formats.
        
        Args:
            data: Input data
            target_format: 'dataframe' or 'dict_list'
            
        Returns:
            Converted data
        """
        if target_format == 'dataframe':
            if isinstance(data, list):
                return pd.DataFrame(data)
            elif isinstance(data, pd.DataFrame):
                return data
        elif target_format == 'dict_list':
            if isinstance(data, pd.DataFrame):
                return data.to_dict('records')
            elif isinstance(data, list):
                return data
        
        raise ValueError(f"Unsupported target format: {target_format}")
    
    def resample_time_series(self, data: pd.DataFrame, new_frequency: str, method: str = 'last'):
        """
        Resample time series data to a different frequency.
        
        Args:
            data: Time series DataFrame
            new_frequency: Target frequency
            method: Resampling method ('last', 'first', 'mean', 'sum')
            
        Returns:
            Resampled DataFrame
        """
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("Data must have a DatetimeIndex for resampling")
        
        if method == 'last':
            return data.resample(new_frequency).last()
        elif method == 'first':
            return data.resample(new_frequency).first()
        elif method == 'mean':
            return data.resample(new_frequency).mean()
        elif method == 'sum':
            return data.resample(new_frequency).sum()
        else:
            raise ValueError(f"Unsupported resampling method: {method}")