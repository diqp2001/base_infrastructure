"""
Feature engineering component for spatiotemporal momentum analysis.

Combines the deep momentum and MACD feature creation from spatiotemporal_momentum_manager
with the factor system architecture from test_project_factor_creation.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date

from src.application.services.data_service.data_service import DataService
from src.application.services.data_service.ratio_data_service import RatioDataService
from src.application.services.database_service.database_service import DatabaseService
from ..config import DEFAULT_CONFIG


class SpatiotemporalFeatureEngineer:
    """
    Feature engineering class that creates sophisticated momentum and technical features
    for spatiotemporal models, integrated with the factor storage system.
    """
    
    def __init__(self, database_service: DatabaseService):
        self.database_service = database_service
        self.config = DEFAULT_CONFIG['SPATIOTEMPORAL']['FEATURES']
        self.data_service = DataService(database_service)
        self.data_manager = RatioDataService(database_service)
    
    def engineer_all_features(self, data: pd.DataFrame, price_column: str = 'close_price') -> pd.DataFrame:
        """
        Create all spatiotemporal features for the given data.
        
        Args:
            data: DataFrame with OHLCV price data
            price_column: Name of the price column to use for feature engineering
            
        Returns:
            DataFrame with all engineered features
        """
        print(f"🔧 Engineering spatiotemporal features for column: {price_column}")
        
        # Make a copy to avoid modifying original data
        feature_data = data.copy()
        
        # Add momentum features using the spatiotemporal approach
        feature_data = self.add_deep_momentum_features(feature_data, price_column)
        
        # Add MACD technical features
        feature_data = self.add_macd_signal_features(feature_data, price_column)
        
        # Add additional technical indicators
        feature_data = self.add_technical_indicators(feature_data, price_column)
        
        # Add volatility features
        feature_data = self.add_volatility_features(feature_data, price_column)
        
        # Add target variables for model training
        feature_data = self.add_target_variables(feature_data, price_column)
        
        print(f"  ✅ Created {len(feature_data.columns) - len(data.columns)} new features")
        
        return feature_data
    
    def add_deep_momentum_features(self, data: pd.DataFrame, column_name: str) -> pd.DataFrame:
        """
        Add deep momentum features using the RatioDataService approach.
        
        Creates normalized returns across multiple timeframes:
        - Daily, monthly, quarterly, biannual, and annual returns
        """
        print("  📈 Adding deep momentum features...")
        
        try:
            # Use the data_manager (RatioDataService)
            enhanced_data = self.data_manager.add_deep_momentum_features(
                data=data, 
                column_name=column_name
            )
            return enhanced_data
            
        except Exception as e:
            print(f"  ⚠️  Error in deep momentum features: {str(e)}")
            # Fallback: create basic momentum features manually
            return self._create_basic_momentum_features(data, column_name)
    
    def _create_basic_momentum_features(self, data: pd.DataFrame, column_name: str) -> pd.DataFrame:
        """Fallback method to create basic momentum features."""
        feature_data = data.copy()
        
        # Calculate returns for different periods
        periods = [1, 5, 21, 63, 252]  # daily, weekly, monthly, quarterly, annual
        
        for period in periods:
            return_col = f'return_{period}d'
            norm_return_col = f'norm_return_{period}d'
            
            # Calculate raw returns
            feature_data[return_col] = feature_data[column_name].pct_change(period)
            
            # Normalize returns (z-score with rolling window)
            rolling_mean = feature_data[return_col].rolling(window=252, min_periods=21).mean()
            rolling_std = feature_data[return_col].rolling(window=252, min_periods=21).std()
            feature_data[norm_return_col] = (feature_data[return_col] - rolling_mean) / rolling_std
        
        return feature_data
    
    def add_macd_signal_features(self, data: pd.DataFrame, column_name: str) -> pd.DataFrame:
        """
        Add MACD signal features using RatioDataService.
        
        Creates MACD indicators across multiple timeframes:
        - 8/24, 16/48, 32/96 period combinations
        """
        print("  📊 Adding MACD signal features...")
        
        # Use the data_manager (RatioDataService)
        enhanced_data = self.data_manager.add_macd_signal_features(
            data=data,
            column_name=column_name
        )
        return enhanced_data
    
    def add_technical_indicators(self, data: pd.DataFrame, column_name: str) -> pd.DataFrame:
        """
        Add additional technical indicators using RatioDataService methods.
        """
        print("  🔧 Adding technical indicators...")
        
        feature_data = data.copy()
        
        # RSI (Relative Strength Index) - using RatioDataService
        feature_data = self.data_manager.add_rsi(feature_data, column_name, period=14)
        
        # Bollinger Bands - using RatioDataService  
        feature_data = self.data_manager.add_bollinger_bands(feature_data, column_name, period=20, std_dev=2)
        
        # Stochastic Oscillator - using RatioDataService
        if 'high_price' in data.columns and 'low_price' in data.columns:
            feature_data = self.data_manager.add_stochastic(feature_data, 'high_price', 'low_price', column_name)
        else:
            feature_data = self.data_manager.add_stochastic(feature_data, column_name, column_name, column_name)
        
        return feature_data