# domain/entities/factor/finance/financial_assets/share_factor/volatility_factor_share_value.py

from dataclasses import dataclass
from typing import Optional, List
from decimal import Decimal
import pandas as pd
import numpy as np

from application.managers.database_managers.database_manager import DatabaseManager
from .volatility_factor_share import VolatilityFactorShare
from domain.entities.factor.finance.financial_assets.share_factor.share_factor_value import ShareFactorValue


@dataclass
class VolatilityFactorShareValue(ShareFactorValue):
    """
    Domain entity representing volatility factor values for shares.
    Follows the same repository storage pattern as MomentumFactorShareValue and TechnicalFactorShareValue.
    """

    factor: Optional[VolatilityFactorShare] = None

    def __init__(self, database_manager: DatabaseManager, factor: VolatilityFactorShare):
        self.factor = factor

    def calculate_daily_volatility(self, returns: pd.Series, period: int = 21) -> pd.Series:
        """Calculate daily volatility (annualized rolling standard deviation)."""
        return returns.rolling(window=period).std() * np.sqrt(252)
    
    def calculate_monthly_volatility(self, returns: pd.Series, period: int = 63) -> pd.Series:
        """Calculate monthly volatility (annualized rolling standard deviation)."""
        return returns.rolling(window=period).std() * np.sqrt(252)
    
    def calculate_volatility_of_volatility(self, daily_vol: pd.Series, period: int = 21) -> pd.Series:
        """Calculate volatility of volatility (vol of vol)."""
        return daily_vol.rolling(window=period).std()
    
    def calculate_realized_volatility(self, returns: pd.Series, period: int = 21) -> pd.Series:
        """Calculate realized volatility (sum of squared returns)."""
        return returns.rolling(window=period).apply(
            lambda x: np.sqrt(np.sum(x**2) * 252)
        )

    def calculate(self, data: pd.DataFrame, column_name: str, volatility_type: str, period: int) -> pd.DataFrame:
        """
        Calculate volatility factor values based on type.
        
        Args:
            data: DataFrame with price data
            column_name: Name of the price column
            volatility_type: Type of volatility calculation
            period: Window size for calculation
            
        Returns:
            DataFrame with volatility values in 'indicator_value' column
        """
        result_data = data.copy()
        
        # Calculate returns if not present
        if 'returns' not in result_data.columns:
            result_data['returns'] = result_data[column_name].pct_change()
        
        # Calculate volatility based on type
        if volatility_type == 'daily_vol':
            result_data['indicator_value'] = self.calculate_daily_volatility(
                result_data['returns'], period
            )
        elif volatility_type == 'monthly_vol':
            result_data['indicator_value'] = self.calculate_monthly_volatility(
                result_data['returns'], period
            )
        elif volatility_type == 'vol_of_vol':
            # First calculate daily volatility, then vol of vol
            daily_vol = self.calculate_daily_volatility(result_data['returns'], 21)
            result_data['indicator_value'] = self.calculate_volatility_of_volatility(
                daily_vol, period
            )
        elif volatility_type == 'realized_vol':
            result_data['indicator_value'] = self.calculate_realized_volatility(
                result_data['returns'], period
            )
        else:
            raise ValueError(f"Unknown volatility type: {volatility_type}")
        
        return result_data

    def store_factor_values(self, repository, factor, share, data: pd.DataFrame, 
                          column_name: str, volatility_type: str, period: int, overwrite: bool) -> int:
        """
        Store volatility factor values using repository pattern.
        Follows same approach as momentum and technical factors.
        
        Args:
            repository: Share factor repository
            factor: Factor entity from repository
            share: Share entity
            data: DataFrame with price data
            column_name: Price column name
            volatility_type: Type of volatility calculation  
            period: Window for volatility calculation
            overwrite: Whether to overwrite existing values
            
        Returns:
            Number of values stored
        """
        try:
            # Calculate volatility values
            calculated_data = self.calculate(data, column_name, volatility_type, period)
            
            # Use repository's _store_factor_values method
            values_stored = repository._store_factor_values(
                factor, share, calculated_data, 'indicator_value', overwrite
            )
            
            return values_stored
            
        except Exception as e:
            print(f"  ⚠️  Error storing {volatility_type} values: {str(e)}")
            return 0