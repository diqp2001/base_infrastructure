# domain/entities/factor/finance/financial_assets/share_factor/technical_factor_share_value.py

from dataclasses import dataclass
from typing import Optional, Dict
from decimal import Decimal
import pandas as pd

from application.managers.database_managers.database_manager import DatabaseManager
from .technical_factor_share import TechnicalFactorShare
from domain.entities.factor.finance.financial_assets.share_factor.share_factor_value import ShareFactorValue


@dataclass
class TechnicalFactorShareValue(ShareFactorValue):
    """
    Domain entity representing technical indicator factor values for a share.
    Follows same pattern as MomentumFactorShareValue with repository storage.
    """

    factor: Optional[TechnicalFactorShare] = None

    def __init__(self, database_manager: DatabaseManager, factor: TechnicalFactorShare):
        self.factor = factor

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands."""
        rolling_mean = prices.rolling(window=period).mean()
        rolling_std = prices.rolling(window=period).std()
        
        return {
            'upper': rolling_mean + (rolling_std * std_dev),
            'lower': rolling_mean - (rolling_std * std_dev),
            'middle': rolling_mean
        }

    def calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                           k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator."""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return {
            'k': k_percent,
            'd': d_percent
        }

    def calculate(self, data: pd.DataFrame, indicator_type: str, period: Optional[int] = None) -> pd.DataFrame:
        """
        Calculate technical indicator values based on type.
        Returns DataFrame with calculated values.
        """
        try:
            # Standardize column names if needed
            if 'Close' in data.columns and 'close_price' not in data.columns:
                data = data.rename(columns={
                    'Open': 'open_price', 'High': 'high_price',
                    'Low': 'low_price', 'Close': 'close_price',
                    'Adj Close': 'adj_close_price', 'Volume': 'volume'
                })

            calculated_df = data.copy()
            
            if indicator_type == "RSI":
                calculated_df['indicator_value'] = self.calculate_rsi(
                    calculated_df['close_price'], period or 14
                )
            elif indicator_type == "Bollinger":
                bollinger = self.calculate_bollinger_bands(calculated_df['close_price'])
                # For this example, use upper band - can be customized per factor
                calculated_df['indicator_value'] = bollinger['upper'] 
            elif indicator_type == "Stochastic":
                stoch = self.calculate_stochastic(
                    calculated_df['high_price'], calculated_df['low_price'], calculated_df['close_price']
                )
                # For this example, use %K - can be customized per factor
                calculated_df['indicator_value'] = stoch['k']
            
            return calculated_df

        except Exception as e:
            print(f"⚠️  Error calculating {indicator_type} features: {e}")
            return pd.DataFrame()

    def store_factor_values(
        self,
        repository,
        factor,
        share,
        data: pd.DataFrame,
        column_name: str,
        indicator_type: str,
        period: Optional[int],
        overwrite: bool
    ) -> int:
        """
        Store technical indicator values using repository pattern.
        Same approach as momentum factors _store_factor_values method.
        """
        try:
            # Calculate technical indicator values
            calculated_df = self.calculate(data=data, indicator_type=indicator_type, period=period)
            if calculated_df.empty:
                return 0

            # Use repository's _store_factor_values method (same as momentum factors)
            values_stored = repository._store_factor_values(
                factor, share, calculated_df, 'indicator_value', overwrite
            )

            return values_stored

        except Exception as e:
            print(f"❌ Error storing {indicator_type} factor values: {e}")
            return 0

    def store_package_technical_factors(
        self,
        repository,
        factor,
        share,
        data: pd.DataFrame,
        column_name: str,
        indicator_type: str,
        period: Optional[int],
        overwrite: bool
    ) -> int:
        """
        Store technical indicator values for a single factor.
        Returns count of stored values (same pattern as momentum factors).
        """
        return self.store_factor_values(
            repository=repository,
            factor=factor,
            share=share,
            data=data,
            column_name=column_name,
            indicator_type=indicator_type,
            period=period,
            overwrite=overwrite
        )