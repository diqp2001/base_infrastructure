# domain/entities/factor/finance/financial_assets/share_factor/target_factor_share_value.py

from dataclasses import dataclass
from typing import Optional, List
from decimal import Decimal
import pandas as pd
import numpy as np

from application.managers.database_managers.database_manager import DatabaseManager
from .target_factor_share import TargetFactorShare
from domain.entities.factor.finance.financial_assets.share_factor.share_factor_value import ShareFactorValue


@dataclass
class TargetFactorShareValue(ShareFactorValue):
    """
    Domain entity representing target variable factor values for shares.
    Follows the same repository storage pattern as other factor value classes.
    """

    factor: Optional[TargetFactorShare] = None

    def __init__(self, database_manager: DatabaseManager, factor: TargetFactorShare):
        self.factor = factor

    def calculate_forward_returns(self, prices: pd.Series, horizon: int = 1) -> pd.Series:
        """Calculate forward returns for target variables."""
        return prices.pct_change(horizon).shift(-horizon)
    
    def calculate_scaled_returns(self, returns: pd.Series, window: int = 252, min_periods: int = 21) -> pd.Series:
        """Calculate z-score normalized returns."""
        rolling_mean = returns.rolling(window=window, min_periods=min_periods).mean()
        rolling_std = returns.rolling(window=window, min_periods=min_periods).std()
        return (returns - rolling_mean) / rolling_std

    def calculate(self, data: pd.DataFrame, column_name: str, target_type: str, 
                 forecast_horizon: int, is_scaled: bool = True) -> pd.DataFrame:
        """
        Calculate target variable values.
        
        Args:
            data: DataFrame with price data
            column_name: Name of the price column
            target_type: Type of target ('target_returns' or 'target_returns_nonscaled')
            forecast_horizon: Number of periods ahead to predict
            is_scaled: Whether to apply scaling/normalization
            
        Returns:
            DataFrame with target values in 'indicator_value' column
        """
        result_data = data.copy()
        
        # Calculate forward returns
        forward_returns = self.calculate_forward_returns(
            result_data[column_name], forecast_horizon
        )
        
        if is_scaled:
            # Apply z-score normalization
            result_data['indicator_value'] = self.calculate_scaled_returns(forward_returns)
        else:
            # Use raw forward returns
            result_data['indicator_value'] = forward_returns
        
        return result_data

    def store_factor_values(self, repository, factor, share, data: pd.DataFrame, 
                          column_name: str, target_type: str, forecast_horizon: int, 
                          is_scaled: bool, overwrite: bool) -> int:
        """
        Store target factor values using repository pattern.
        Follows same approach as momentum, technical, and volatility factors.
        
        Args:
            repository: Share factor repository
            factor: Factor entity from repository
            share: Share entity
            data: DataFrame with price data
            column_name: Price column name
            target_type: Type of target variable
            forecast_horizon: Number of periods ahead to predict
            is_scaled: Whether to apply scaling
            overwrite: Whether to overwrite existing values
            
        Returns:
            Number of values stored
        """
        try:
            # Calculate target values
            calculated_data = self.calculate(
                data, column_name, target_type, forecast_horizon, is_scaled
            )
            
            # Use repository's _store_factor_values method
            values_stored = repository._store_factor_values(
                factor, share, calculated_data, 'indicator_value', overwrite
            )
            
            return values_stored
            
        except Exception as e:
            print(f"  ⚠️  Error storing {target_type} values: {str(e)}")
            return 0