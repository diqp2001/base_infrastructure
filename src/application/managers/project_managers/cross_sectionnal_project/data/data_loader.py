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

from src.application.services.data_service.train_val_test_splitter_service import MultivariateTrainValTestSplitterService, UnivariateTrainValTestSplitterService
from src.application.services.database_service.database_service import DatabaseService
from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository

from ..config import DEFAULT_CONFIG


class DataLoader:
    """
    Data loader that combines factor-based data retrieval with 
    spatiotemporal tensor preparation for ML models.
    """
    
    def __init__(self, database_service: DatabaseService):
        self.database_service = database_service
        self.config = DEFAULT_CONFIG['DATA']
        self.spatiotemporal_config = DEFAULT_CONFIG['SPATIOTEMPORAL']
        
        # Initialize repositories initialize all repo in a service
        self.company_share_repository = CompanyShareRepositoryLocal(database_service.session)
        self.share_factor_repository = ShareFactorRepository(database_service.session)
        
        # Data paths - find project root by looking for data/stock_data directory
        current_path = Path(__file__).resolve()
        self.project_root = current_path
        
        # Walk up the directory tree to find the project root
        while not (self.project_root / 'data' / 'stock_data').exists() and self.project_root.parent != self.project_root:
            self.project_root = self.project_root.parent
            
        self.stock_data_path = self.project_root / "data" / "stock_data"
    
    def load_historical_data_with_factors(self, 
                                        tickers: Optional[List[str]] = None,
                                        start_date: Optional[str] = None,
                                        end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Load historical data directly from CSV files.
        
        Since the factor system was removed, this method now loads data 
        directly from CSV files in the /data/stock_data/ directory.
        
        Args:
            tickers: List of stock tickers to load
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            DataFrame with price data loaded from CSV files
        """
        if tickers is None:
            tickers = self.config['DEFAULT_UNIVERSE']
        
        print(f"📊 Loading historical data for {len(tickers)} tickers from CSV files...")
        
        # Load data from CSV files instead of factor system
        combined_data = {}
        
        for ticker in tickers:
            # Load CSV data (primary source since factor system was removed)
            csv_data = self._load_csv_data(ticker, start_date, end_date)
            
            if csv_data is not None and not csv_data.empty:
                combined_data[ticker] = csv_data
                print(f"  ✅ Loaded {len(csv_data)} records for {ticker}")
            else:
                print(f"  ❌ No CSV data found for {ticker}")
        
        if not combined_data:
            raise ValueError("No data loaded for any ticker. Check that CSV files exist in /data/stock_data/.")
        
        # Convert to the format expected by spatiotemporal models
        return self._format_for_base_df_processing(combined_data)
    
    def _load_csv_data(self, ticker: str, start_date: Optional[str], end_date: Optional[str]) -> Optional[pd.DataFrame]:
        """
        Load historical price data from CSV files.
        
        This is now the primary method for loading historical data since 
        the factor system was removed from the codebase.
        """
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
            share = self.company_share_repository.get_by_ticker(ticker)[0]
            if not share:
                print(f"  ⚠️  Company share not found for ticker: {ticker}")
                return None
            
            # Get factor values for this share
            factor_data = {}
            
            # Load basic price factors (these should exist after setup_factor_system)
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
                    else:
                        print(f"  ⚠️  No values found for factor '{factor_name}' for {ticker}")
                else:
                    print(f"  ⚠️  Factor '{factor_name}' not found in database")
            
            if not factor_data:
                print(f"  ❌ No factor data found for {ticker}. Check if setup_factor_system() was run.")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(factor_data)
            
            # Ensure the index is properly sorted
            df = df.sort_index()
            df.index.name = 'Date'
            
            print(f"  📈 Loaded {len(df)} factor records for {ticker} with columns: {list(df.columns)}")
            return df
            
        except Exception as e:
            print(f"  ❌ Error loading factor data for {ticker}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _format_for_base_df_processing(self, data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
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
        combined_df = combined_df.ffill().bfill()
        
        return combined_df
    
    
    
    
    
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