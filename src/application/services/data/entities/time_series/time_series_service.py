#src/application/services/data/entities/time_series/time_series_service.py

"""
Time Series Service - handles creation and management of time series entities.
Provides a service layer for creating time series domain entities like TimeSeries, FinancialAssetTimeSeries, etc.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.domain.entities.time_series.time_series import TimeSeries
from src.domain.entities.time_series.dask_time_series import DaskTimeSeries
from src.domain.entities.time_series.finance.stock_time_series import StockTimeSeries
from src.domain.entities.time_series.finance.financial_asset_time_series import FinancialAssetTimeSeries
from src.domain.entities.time_series.ml.ml_time_series import MlTimeSeries

# Import existing repositories
from src.infrastructure.repositories.local_repo.time_series.time_series_repository import TimeSeriesRepository
from src.infrastructure.repositories.local_repo.time_series.stock_time_series_repository import StockTimeSeriesRepository
from src.infrastructure.repositories.local_repo.time_series.financial_asset_time_series_repository import FinancialAssetTimeSeriesRepository
from src.application.services.database_service.database_service import DatabaseService


class TimeSeriesService:
    """Service for creating and managing time series domain entities."""
    
    def __init__(self, database_service: Optional[DatabaseService] = None, db_type: str = 'sqlite'):
        """
        Initialize the service with a database service or create one if not provided.
        
        Args:
            database_service: Optional existing DatabaseService instance
            db_type: Database type to use when creating new DatabaseService (ignored if database_service provided)
        """
        if database_service is not None:
            self.database_service = database_service
        else:
            self.database_service = DatabaseService(db_type)
        self._init_repositories()
    
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
    ) -> MlTimeSeries:
        """Create an MLTimeSeries entity for machine learning purposes."""
        return MlTimeSeries(
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
    
    def create_ml_time_series_from_config(self, config: Dict[str, Any]) -> MlTimeSeries:
        """Create an MlTimeSeries from configuration."""
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
    
    def _init_repositories(self):
        """Initialize database repositories using DatabaseService."""
        # Use the shared database service session for all repositories
        session = self.database_service.session
        
        # Initialize existing repositories
        self.time_series_repository = TimeSeriesRepository(session) if hasattr(TimeSeriesRepository, '__init__') else None
        self.stock_time_series_repository = StockTimeSeriesRepository(session) if hasattr(StockTimeSeriesRepository, '__init__') else None
        self.financial_asset_time_series_repository = FinancialAssetTimeSeriesRepository(session) if hasattr(FinancialAssetTimeSeriesRepository, '__init__') else None
    
    # Persistence Methods
    def persist_time_series(self, time_series: TimeSeries) -> Optional[TimeSeries]:
        """
        Persist a time series entity to the database.
        
        Args:
            time_series: TimeSeries entity to persist
            
        Returns:
            Persisted time series entity or None if failed
        """
        try:
            if self.time_series_repository:
                return self.time_series_repository.add(time_series)
            else:
                print("TimeSeries repository not available")
                return None
        except Exception as e:
            print(f"Error persisting time series {time_series.name}: {str(e)}")
            return None
    
    def persist_stock_time_series(self, stock_time_series: StockTimeSeries) -> Optional[StockTimeSeries]:
        """
        Persist a stock time series entity to the database.
        
        Args:
            stock_time_series: StockTimeSeries entity to persist
            
        Returns:
            Persisted stock time series entity or None if failed
        """
        try:
            if self.stock_time_series_repository:
                return self.stock_time_series_repository.add(stock_time_series)
            else:
                print("StockTimeSeries repository not available")
                return None
        except Exception as e:
            print(f"Error persisting stock time series {stock_time_series.symbol if hasattr(stock_time_series, 'symbol') else stock_time_series.name}: {str(e)}")
            return None
    
    def persist_financial_asset_time_series(self, financial_asset_time_series: FinancialAssetTimeSeries) -> Optional[FinancialAssetTimeSeries]:
        """
        Persist a financial asset time series entity to the database.
        
        Args:
            financial_asset_time_series: FinancialAssetTimeSeries entity to persist
            
        Returns:
            Persisted financial asset time series entity or None if failed
        """
        try:
            if self.financial_asset_time_series_repository:
                return self.financial_asset_time_series_repository.add(financial_asset_time_series)
            else:
                print("FinancialAssetTimeSeries repository not available")
                return None
        except Exception as e:
            print(f"Error persisting financial asset time series {financial_asset_time_series.asset_id if hasattr(financial_asset_time_series, 'asset_id') else 'unknown'}: {str(e)}")
            return None
    
    def persist_dask_time_series(self, dask_time_series: DaskTimeSeries) -> Optional[DaskTimeSeries]:
        """
        Persist a dask time series entity to the database.
        Note: This is a placeholder implementation - add specific repository when available.
        
        Args:
            dask_time_series: DaskTimeSeries entity to persist
            
        Returns:
            Persisted dask time series entity or None if failed
        """
        try:
            print(f"Warning: DaskTimeSeries persistence not yet implemented for {dask_time_series.name}")
            return dask_time_series
        except Exception as e:
            print(f"Error persisting dask time series: {str(e)}")
            return None
    
    def persist_ml_time_series(self, ml_time_series: MlTimeSeries) -> Optional[MlTimeSeries]:
        """
        Persist an ML time series entity to the database.
        Note: This is a placeholder implementation - add specific repository when available.
        
        Args:
            ml_time_series: MlTimeSeries entity to persist
            
        Returns:
            Persisted ML time series entity or None if failed
        """
        try:
            print(f"Warning: MlTimeSeries persistence not yet implemented for {ml_time_series.name if hasattr(ml_time_series, 'name') else 'unknown'}")
            return ml_time_series
        except Exception as e:
            print(f"Error persisting ML time series: {str(e)}")
            return None
    
    # Pull Methods (Retrieve from database)
    def pull_time_series_by_id(self, time_series_id: int) -> Optional[TimeSeries]:
        """Pull time series by ID from database."""
        try:
            if self.time_series_repository:
                return self.time_series_repository.get_by_id(time_series_id)
            else:
                print("TimeSeries repository not available")
                return None
        except Exception as e:
            print(f"Error pulling time series by ID {time_series_id}: {str(e)}")
            return None
    
    def pull_stock_time_series_by_id(self, stock_time_series_id: int) -> Optional[StockTimeSeries]:
        """Pull stock time series by ID from database."""
        try:
            if self.stock_time_series_repository:
                return self.stock_time_series_repository.get_by_id(stock_time_series_id)
            else:
                print("StockTimeSeries repository not available")
                return None
        except Exception as e:
            print(f"Error pulling stock time series by ID {stock_time_series_id}: {str(e)}")
            return None
    
    def pull_stock_time_series_by_symbol(self, symbol: str) -> Optional[StockTimeSeries]:
        """Pull stock time series by symbol from database."""
        try:
            if self.stock_time_series_repository and hasattr(self.stock_time_series_repository, 'get_by_symbol'):
                return self.stock_time_series_repository.get_by_symbol(symbol)
            else:
                print("StockTimeSeries repository not available or method not implemented")
                return None
        except Exception as e:
            print(f"Error pulling stock time series by symbol {symbol}: {str(e)}")
            return None
    
    def pull_financial_asset_time_series_by_id(self, financial_asset_time_series_id: int) -> Optional[FinancialAssetTimeSeries]:
        """Pull financial asset time series by ID from database."""
        try:
            if self.financial_asset_time_series_repository:
                return self.financial_asset_time_series_repository.get_by_id(financial_asset_time_series_id)
            else:
                print("FinancialAssetTimeSeries repository not available")
                return None
        except Exception as e:
            print(f"Error pulling financial asset time series by ID {financial_asset_time_series_id}: {str(e)}")
            return None
    
    def pull_financial_asset_time_series_by_asset_id(self, asset_id: str) -> List[FinancialAssetTimeSeries]:
        """Pull financial asset time series by asset ID from database."""
        try:
            if self.financial_asset_time_series_repository and hasattr(self.financial_asset_time_series_repository, 'get_by_asset_id'):
                return self.financial_asset_time_series_repository.get_by_asset_id(asset_id)
            else:
                print("FinancialAssetTimeSeries repository not available or method not implemented")
                return []
        except Exception as e:
            print(f"Error pulling financial asset time series by asset ID {asset_id}: {str(e)}")
            return []
    
    def pull_all_time_series(self) -> List[TimeSeries]:
        """Pull all time series from database."""
        try:
            if self.time_series_repository:
                return self.time_series_repository.get_all()
            else:
                print("TimeSeries repository not available")
                return []
        except Exception as e:
            print(f"Error pulling all time series: {str(e)}")
            return []
    
    def pull_all_stock_time_series(self) -> List[StockTimeSeries]:
        """Pull all stock time series from database."""
        try:
            if self.stock_time_series_repository:
                return self.stock_time_series_repository.get_all()
            else:
                print("StockTimeSeries repository not available")
                return []
        except Exception as e:
            print(f"Error pulling all stock time series: {str(e)}")
            return []