# domain/entities/factor/finance/financial_assets/share_factor/technical_factor_share_value.py

from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal
import pandas as pd

from application.managers.database_managers.database_manager import DatabaseManager
from .technical_factor_share import TechnicalFactorShare
from domain.entities.factor.finance.financial_assets.share_factor.share_factor_value import ShareFactorValue
from infrastructure.models.factor.finance.financial_assets.share_factors import ShareFactorValue


class TechnicalFactorShareValue(ShareFactorValue):
    """Value calculator and storage handler for technical indicator factors."""

    def __init__(self, database_manager: DatabaseManager, factor: TechnicalFactorShare):
        super().__init__(database_manager, factor)
        self.technical_factor = factor

    def _sanitize_factor_value(self, value) -> Optional[Decimal]:
        """
        Sanitize and validate factor values to handle ANY data type safely.
        Prevents type comparison errors with string values.
        """
        if value is None or pd.isna(value):
            return None
            
        if isinstance(value, Decimal):
            return value if value.is_finite() else None
            
        str_value = str(value).strip()
        invalid_indicators = {'', 'n/a', 'na', 'null', 'none', 'nan', '-', '--', 'inf', '-inf'}
        if str_value.lower() in invalid_indicators:
            return None
            
        try:
            float_value = float(str_value)
            if not (float_value == float_value and abs(float_value) != float('inf')):
                return None
            return Decimal(str(float_value))
        except (ValueError, TypeError, OverflowError, Decimal.InvalidOperation):
            return None
    
    def store_package_technical_factors(
        self,
        data: pd.DataFrame,
        column_name: str,
        entity_id: int,
        factor_id: int,
        indicator_type: str
    ) -> List[ShareFactorValue]:
        """
        Store technical indicator values as factor values.
        
        Args:
            data: DataFrame with technical indicator values
            column_name: Column containing the indicator values
            entity_id: Company share entity ID
            factor_id: Factor ID in the database
            indicator_type: Type of technical indicator
            
        Returns:
            List of ShareFactorValue ORM objects ready for database storage
        """
        orm_values = []
        
        for index, row in data.iterrows():
            if pd.isna(row[column_name]):
                continue
                
            # Handle datetime index
            trade_date = index.date() if isinstance(index, datetime) else index
            
            try:
                # Sanitize value to prevent type comparison errors
                sanitized_value = self._sanitize_factor_value(row[column_name])
                if sanitized_value is None:
                    continue  # Skip invalid values
                    
                # Create ORM object
                orm_value = ShareFactorValue(
                    factor_id=factor_id,
                    entity_id=entity_id,
                    date=trade_date,
                    value=sanitized_value
                )
                orm_values.append(orm_value)
                
            except (ValueError, TypeError) as e:
                print(f"      ⚠️  Error processing {indicator_type} value for {trade_date}: {str(e)}")
                continue
        
        return orm_values

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