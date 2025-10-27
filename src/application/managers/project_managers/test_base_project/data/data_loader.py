"""
Data loading component for spatiotemporal momentum analysis.

Combines CSV data loading capabilities from test_project_factor_creation
with the data preprocessing patterns from spatiotemporal_momentum_manager.
"""

import os
import pandas as pd
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.data_managers.machine_learning.multivariate_train_val_test_splitter import MultivariateTrainValTestSplitter
from application.managers.data_managers.machine_learning.univariate_train_val_test_splitter import UnivariateTrainValTestSplitter
from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal
from infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository

from ..config import DEFAULT_CONFIG


class SpatiotemporalDataLoader:
    """
    Data loader that combines factor-based data retrieval with 
    spatiotemporal tensor preparation for ML models.
    """
    
    def __init__(self, database_manager: DatabaseManager):
        self.database_manager = database_manager
        self.config = DEFAULT_CONFIG['DATA']
        self.spatiotemporal_config = DEFAULT_CONFIG['SPATIOTEMPORAL']
        
        # Initialize repositories
        self.company_share_repository = CompanyShareRepositoryLocal(database_manager.session)
        self.share_factor_repository = ShareFactorRepository(DEFAULT_CONFIG['DATABASE']['DB_TYPE'])
        
        # Data paths
        self.project_root = Path(__file__).parent.parent.parent.parent.parent.parent
        self.stock_data_path = self.project_root / "data" / "stock_data"
    
    def load_historical_data_with_factors(self, 
                                        tickers: Optional[List[str]] = None,
                                        start_date: Optional[str] = None,
                                        end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Load historical data combining CSV sources with factor system data.
        
        Args:
            tickers: List of stock tickers to load
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Combined DataFrame with price data and factor values
        """
        if tickers is None:
            tickers = self.config['DEFAULT_UNIVERSE']
        
        print(f"📊 Loading historical data for {len(tickers)} tickers...")
        
        # Load data from both CSV and factor system
        combined_data = {}
        
        for ticker in tickers:
            # Load CSV data (primary source)
            csv_data = self._load_csv_data(ticker, start_date, end_date)
            
            # Load factor data (enhanced features)
            factor_data = self._load_factor_data(ticker, start_date, end_date)
            
            # Combine the data sources
            if csv_data is not None and not csv_data.empty:
                # Merge factor data if available
                if factor_data is not None and not factor_data.empty:
                    combined = csv_data.merge(factor_data, left_index=True, right_index=True, how='left')
                else:
                    combined = csv_data.copy()
                
                combined_data[ticker] = combined
                print(f"  ✅ Loaded {len(combined)} records for {ticker}")
            else:
                print(f"  ❌ No data found for {ticker}")
        
        if not combined_data:
            raise ValueError("No data loaded for any ticker")
        
        # Convert to the format expected by spatiotemporal models
        return self._format_for_spatiotemporal_processing(combined_data)
    
    def _load_csv_data(self, ticker: str, start_date: Optional[str], end_date: Optional[str]) -> Optional[pd.DataFrame]:
        """Load historical price data from CSV files."""
        csv_file = self.stock_data_path / f"{ticker}.csv"
        
        if not csv_file.exists():
            print(f"  ⚠️  CSV file not found: {csv_file}")
            return None
        
        try:
            df = pd.read_csv(csv_file)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            
            # Filter by date range if specified
            if start_date:
                df = df[df.index >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df.index <= pd.to_datetime(end_date)]
            
            # Standardize column names
            column_mapping = {
                'Open': 'open_price',
                'High': 'high_price', 
                'Low': 'low_price',
                'Close': 'close_price',
                'Adj Close': 'adj_close_price',
                'Volume': 'volume'
            }
            
            df = df.rename(columns=column_mapping)
            return df
            
        except Exception as e:
            print(f"  ❌ Error loading CSV for {ticker}: {str(e)}")
            return None
    
    def _load_factor_data(self, ticker: str, start_date: Optional[str], end_date: Optional[str]) -> Optional[pd.DataFrame]:
        """Load factor data from the factor system."""
        try:
            # Get the company share entity
            share = self.company_share_repository.get_by_ticker(ticker)
            if not share:
                return None
            
            # Get factor values for this share
            factor_data = {}
            
            # Load basic price factors
            price_factors = ['open_price', 'high_price', 'low_price', 'close_price', 'adj_close_price', 'volume']
            for factor_name in price_factors:
                factor = self.share_factor_repository.get_by_name(factor_name)
                if factor:
                    values = self.share_factor_repository.get_factor_values(
                        factor.id, share.id, start_date, end_date
                    )
                    if values:
                        factor_data[factor_name] = {
                            pd.to_datetime(v.date): float(v.value) for v in values
                        }
            
            if not factor_data:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(factor_data)
            df.index.name = 'Date'
            
            return df
            
        except Exception as e:
            print(f"  ⚠️  Error loading factor data for {ticker}: {str(e)}")
            return None
    
    def _format_for_spatiotemporal_processing(self, data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Format the loaded data for spatiotemporal model processing.
        
        This creates a unified DataFrame structure similar to what 
        spatiotemporal_momentum_manager expects.
        """
        # Create a multi-level DataFrame with tickers as columns
        all_data = []
        
        for ticker, df in data_dict.items():
            # Add ticker information
            df_copy = df.copy()
            df_copy.columns = [f"{ticker}_{col}" for col in df_copy.columns]
            all_data.append(df_copy)
        
        # Combine all ticker data
        combined_df = pd.concat(all_data, axis=1)
        combined_df = combined_df.sort_index()
        
        # Fill missing values using forward fill then backward fill
        combined_df = combined_df.fillna(method='ffill').fillna(method='bfill')
        
        return combined_df
    
    def prepare_multivariate_tensors(self, 
                                   data: pd.DataFrame,
                                   target_col: str = 'target_returns',
                                   timesteps: int = 63,
                                   batch_size: int = 64,
                                   encoder_length: Optional[int] = None) -> MultivariateTrainValTestSplitter:
        """
        Prepare multivariate tensors for TFT model training.
        
        Args:
            data: Processed DataFrame with features
            target_col: Name of target column
            timesteps: Number of timesteps for sequences
            batch_size: Batch size for training
            encoder_length: Encoder length for TFT (if None, uses config)
            
        Returns:
            MultivariateTrainValTestSplitter ready for model training
        """
        if encoder_length is None:
            encoder_length = self.spatiotemporal_config['TRAINING_CONFIG']['encoder_length']
        
        # Extract feature columns (non-target columns)
        feature_cols = [col for col in data.columns if target_col not in col]
        categorical_cols = []  # Add categorical columns if needed
        
        # Prepare additional columns needed by the splitter
        orig_returns_col = f'{target_col}_nonscaled'
        vol_col = 'daily_vol'
        
        # Create the splitter
        splitter = MultivariateTrainValTestSplitter(
            data=data,
            cols=feature_cols,
            cat_cols=categorical_cols,
            target_col=target_col,
            orig_returns_col=orig_returns_col,
            vol_col=vol_col,
            timesteps=timesteps,
            scaling=self.spatiotemporal_config['TRAINING_CONFIG'].get('scaling'),
            batch_size=batch_size,
            encoder_length=encoder_length
        )
        
        return splitter
    
    def prepare_univariate_tensors(self,
                                 data: Dict[str, pd.DataFrame],
                                 target_col: str = 'target_returns',
                                 timesteps: int = 21,
                                 encoder_length: Optional[int] = None) -> UnivariateTrainValTestSplitter:
        """
        Prepare univariate tensors for MLP model training.
        
        Args:
            data: Dictionary of DataFrames per asset
            target_col: Name of target column
            timesteps: Number of timesteps for sequences
            encoder_length: Encoder length (None for MLP)
            
        Returns:
            UnivariateTrainValTestSplitter ready for model training
        """
        # Add asset information to each DataFrame
        for asset, df in data.items():
            df['asset'] = asset
        
        # Get feature columns from configuration
        feature_cols = (
            self.spatiotemporal_config['FEATURES']['momentum_features'] +
            self.spatiotemporal_config['FEATURES']['technical_features']
        )
        
        categorical_cols = ['asset'] if len(data) > 1 else []
        orig_returns_col = f'{target_col}_nonscaled'
        vol_col = 'daily_vol'
        
        # Create the splitter
        splitter = UnivariateTrainValTestSplitter(
            data=data,
            cols=feature_cols,
            cat_cols=categorical_cols,
            target_col=target_col,
            orig_returns_col=orig_returns_col,
            vol_col=vol_col,
            scaling=self.spatiotemporal_config['TRAINING_CONFIG'].get('scaling'),
            timesteps=timesteps,
            encoder_length=encoder_length,
            use_asset_info_as_feature=len(data) > 1
        )
        
        return splitter
    
    def create_factor_features(self, data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """
        Create factor-based features ready for model input.
        
        This method bridges the gap between raw price data and the 
        feature engineering expected by spatiotemporal models.
        """
        # This will be implemented by the FeatureEngineer class
        # Here we just return the data as-is for now
        return data
    
    def validate_data_quality(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate the quality of loaded data."""
        quality_report = {
            'total_records': len(data),
            'date_range': (data.index.min(), data.index.max()),
            'missing_values': data.isnull().sum().to_dict(),
            'columns': list(data.columns),
            'duplicated_dates': data.index.duplicated().sum(),
            'data_quality_score': 0.0
        }
        
        # Calculate data quality score (0-100)
        total_cells = len(data) * len(data.columns)
        missing_cells = data.isnull().sum().sum()
        quality_report['data_quality_score'] = ((total_cells - missing_cells) / total_cells) * 100
        
        return quality_report