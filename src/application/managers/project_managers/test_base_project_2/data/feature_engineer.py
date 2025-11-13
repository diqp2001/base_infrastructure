"""
Feature engineering component for spatiotemporal momentum analysis.

Combines the deep momentum and MACD feature creation from spatiotemporal_momentum_manager
with the factor system architecture from test_project_factor_creation.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date

from application.managers.data_managers.data_manager_ratio import DataManagerRatio
from application.managers.database_managers.database_manager import DatabaseManager
from ..config import DEFAULT_CONFIG


class SpatiotemporalFeatureEngineer:
    """
    Feature engineering class that creates sophisticated momentum and technical features
    for spatiotemporal models, integrated with the factor storage system.
    """
    
    def __init__(self, database_manager: DatabaseManager):
        self.database_manager = database_manager
        self.config = DEFAULT_CONFIG['SPATIOTEMPORAL']['FEATURES']
        self.data_manager = DataManagerRatio(self.database_manager)
    
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
        Add deep momentum features using the spatiotemporal_momentum_manager approach.
        
        Creates normalized returns across multiple timeframes:
        - Daily, monthly, quarterly, biannual, and annual returns
        """
        print("  📈 Adding deep momentum features...")
        
        try:
            # Use the data_manager from spatiotemporal_momentum_manager
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
        Add MACD signal features using DataManagerRatio.
        
        Creates MACD indicators across multiple timeframes:
        - 8/24, 16/48, 32/96 period combinations
        """
        print("  📊 Adding MACD signal features...")
        
        # Use the data_manager from DataManagerRatio (moved from feature_engineer)
        enhanced_data = self.data_manager.add_macd_signal_features(
            data=data,
            column_name=column_name
        )
        return enhanced_data
    
    def _create_basic_macd_features(self, data: pd.DataFrame, column_name: str) -> pd.DataFrame:
        """Fallback method to create basic MACD features."""
        feature_data = data.copy()
        
        # MACD parameter combinations from config
        macd_params = [
            (8, 24),
            (16, 48), 
            (32, 96)
        ]
        
        for fast, slow in macd_params:
            macd_col = f'macd_{fast}_{slow}'
            signal_col = f'macd_signal_{fast}_{slow}'
            histogram_col = f'macd_histogram_{fast}_{slow}'
            
            # Calculate MACD
            ema_fast = feature_data[column_name].ewm(span=fast).mean()
            ema_slow = feature_data[column_name].ewm(span=slow).mean()
            
            feature_data[macd_col] = ema_fast - ema_slow
            feature_data[signal_col] = feature_data[macd_col].ewm(span=9).mean()
            feature_data[histogram_col] = feature_data[macd_col] - feature_data[signal_col]
        
        return feature_data
    
    def add_volatility_features(self, data: pd.DataFrame, column_name: str) -> pd.DataFrame:
        """
        Add volatility features using new domain classes and factor manager pattern.
        """
        print("  📉 Adding volatility features using domain classes...")
        
        from domain.entities.factor.finance.financial_assets.share_factor.volatility_factor_share_value import VolatilityFactorShareValue
        from domain.entities.factor.finance.financial_assets.share_factor.volatility_factor_share import ShareVolatilityFactor
        
        feature_data = data.copy()
        
        volatility_configs = [
            {'name': 'daily_vol', 'volatility_type': 'daily_vol', 'period': 21},
            {'name': 'monthly_vol', 'volatility_type': 'monthly_vol', 'period': 63},
            {'name': 'vol_of_vol', 'volatility_type': 'vol_of_vol', 'period': 21},
            {'name': 'realized_vol', 'volatility_type': 'realized_vol', 'period': 21}
        ]
        
        for vol_config in volatility_configs:
            # Create domain entity
            volatility_entity = ShareVolatilityFactor(
                name=vol_config['name'],
                factor_type='volatility',
                description=f"Volatility: {vol_config['volatility_type']}",
                volatility_type=vol_config['volatility_type'],
                period=vol_config['period']
            )
            
            # Create calculator
            vol_calculator = VolatilityFactorShareValue(self.database_manager, volatility_entity)
            
            # Calculate values and add to feature data
            calculated_data = vol_calculator.calculate(
                data=feature_data,
                column_name=column_name,
                volatility_type=vol_config['volatility_type'],
                period=vol_config['period']
            )
            
            # Add the calculated column to feature data
            feature_data[vol_config['name']] = calculated_data['indicator_value']
        
        return feature_data
    
    def add_target_variables(self, data: pd.DataFrame, column_name: str, freq: int = 1) -> pd.DataFrame:
        """
        Add target variables using new domain classes and factor manager pattern.
        
        Creates both scaled and non-scaled target returns for model training.
        """
        print("  🎯 Adding target variables using domain classes...")
        
        from domain.entities.factor.finance.financial_assets.share_factor.target_factor_share_value import ShareTargetFactorValue
        from domain.entities.factor.finance.financial_assets.share_factor.target_factor_share import ShareTargetFactor
        
        feature_data = data.copy()
        
        target_configs = [
            {'name': 'target_returns', 'target_type': 'target_returns', 'forecast_horizon': freq, 'is_scaled': True},
            {'name': 'target_returns_nonscaled', 'target_type': 'target_returns_nonscaled', 'forecast_horizon': freq, 'is_scaled': False}
        ]
        
        for target_config in target_configs:
            # Create domain entity
            target_entity = ShareTargetFactor(
                name=target_config['name'],
                factor_type='target',
                description=f"Target: {target_config['target_type']}",
                target_type=target_config['target_type'],
                forecast_horizon=target_config['forecast_horizon'],
                is_scaled=target_config['is_scaled']
            )
            
            # Create calculator
            target_calculator = ShareTargetFactorValue(self.database_manager, target_entity)
            
            # Calculate values and add to feature data
            calculated_data = target_calculator.calculate(
                data=feature_data,
                column_name=column_name,
                target_type=target_config['target_type'],
                forecast_horizon=target_config['forecast_horizon'],
                is_scaled=target_config['is_scaled']
            )
            
            # Add the calculated column to feature data
            feature_data[target_config['name']] = calculated_data['indicator_value']
        
        return feature_data
    
    def _create_basic_targets(self, data: pd.DataFrame, column_name: str, freq: int = 1) -> pd.DataFrame:
        """Fallback method to create basic target variables."""
        feature_data = data.copy()
        
        # Forward returns (target)
        feature_data['target_returns'] = feature_data[column_name].pct_change(freq).shift(-freq)
        feature_data['target_returns_nonscaled'] = feature_data['target_returns'].copy()
        
        # Normalize target returns
        rolling_mean = feature_data['target_returns'].rolling(window=252, min_periods=21).mean()
        rolling_std = feature_data['target_returns'].rolling(window=252, min_periods=21).std()
        feature_data['target_returns'] = (feature_data['target_returns'] - rolling_mean) / rolling_std
        
        return feature_data
    
    def add_technical_indicators(self, data: pd.DataFrame, column_name: str) -> pd.DataFrame:
        """
        Add additional technical indicators using DataManagerRatio methods.
        """
        print("  🔧 Adding technical indicators...")
        
        feature_data = data.copy()
        
        # RSI (Relative Strength Index) - using DataManagerRatio
        feature_data = self.data_manager.add_rsi(feature_data, column_name, period=14)
        
        # Bollinger Bands - using DataManagerRatio  
        feature_data = self.data_manager.add_bollinger_bands(feature_data, column_name, period=20, std_dev=2)
        
        # Stochastic Oscillator - using DataManagerRatio
        if 'high_price' in data.columns and 'low_price' in data.columns:
            feature_data = self.data_manager.add_stochastic(feature_data, 'high_price', 'low_price', column_name)
        else:
            feature_data = self.data_manager.add_stochastic(feature_data, column_name, column_name, column_name)
        
        return feature_data
    
    def _add_rsi(self, data: pd.DataFrame, column_name: str, period: int = 14) -> pd.DataFrame:
        """Add RSI indicator."""
        delta = data[column_name].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        data[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        
        return data
    
    def _add_bollinger_bands(self, data: pd.DataFrame, column_name: str, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
        """Add Bollinger Bands."""
        rolling_mean = data[column_name].rolling(window=period).mean()
        rolling_std = data[column_name].rolling(window=period).std()
        
        data['bollinger_middle'] = rolling_mean
        data['bollinger_upper'] = rolling_mean + (rolling_std * std_dev)
        data['bollinger_lower'] = rolling_mean - (rolling_std * std_dev)
        data['bollinger_width'] = data['bollinger_upper'] - data['bollinger_lower']
        data['bollinger_position'] = (data[column_name] - data['bollinger_lower']) / data['bollinger_width']
        
        return data
    
    def _add_stochastic(self, data: pd.DataFrame, high_col: str, low_col: str, close_col: str, k_period: int = 14) -> pd.DataFrame:
        """Add Stochastic Oscillator."""
        lowest_low = data[low_col].rolling(window=k_period).min()
        highest_high = data[high_col].rolling(window=k_period).max()
        
        data['stoch_k'] = 100 * (data[close_col] - lowest_low) / (highest_high - lowest_low)
        data['stoch_d'] = data['stoch_k'].rolling(window=3).mean()
        
        return data
    
    def prepare_training_data(self, data: pd.DataFrame, 
                            column_name: str = 'close_price') -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Prepare data for machine learning training following spatiotemporal_momentum_manager pattern.
        
        Returns:
            Tuple of (full_data, features, targets)
        """
        print("🎯 Preparing training data...")
        
        # Engineer all features
        engineered_data = self.engineer_all_features(data, column_name)
        
        # Split features and targets
        target_columns = ['target_returns', 'target_returns_nonscaled']
        feature_columns = [col for col in engineered_data.columns 
                          if col not in target_columns + [column_name]]
        
        features = engineered_data[feature_columns]
        targets = engineered_data[target_columns]
        
        # Drop rows with NaN values
        combined_data = pd.concat([features, targets], axis=1).dropna()
        
        final_features = combined_data[feature_columns]
        final_targets = combined_data[target_columns]
        
        print(f"  ✅ Training data prepared: {len(final_features)} samples, {len(feature_columns)} features")
        
        return combined_data, final_features, final_targets
    
    def get_feature_importance_mapping(self) -> Dict[str, str]:
        """
        Return mapping of feature names to their descriptions for interpretability.
        """
        return {
            'norm_daily_return': 'Normalized 1-day return',
            'norm_monthly_return': 'Normalized 21-day return', 
            'norm_quarterly_return': 'Normalized 63-day return',
            'norm_biannual_return': 'Normalized 126-day return',
            'norm_annual_return': 'Normalized 252-day return',
            'macd_8_24': 'MACD (8,24) line',
            'macd_16_48': 'MACD (16,48) line',
            'macd_32_96': 'MACD (32,96) line',
            'daily_vol': '21-day rolling volatility',
            'monthly_vol': '63-day rolling volatility',
            'rsi_14': '14-period RSI',
            'bollinger_upper': 'Bollinger upper band',
            'bollinger_lower': 'Bollinger lower band',
            'stoch_k': 'Stochastic %K',
            'stoch_d': 'Stochastic %D'
        }