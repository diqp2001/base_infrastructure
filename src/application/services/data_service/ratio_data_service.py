import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from ..database_service.database_service import DatabaseService
from .data_service import DataService


class RatioDataService(DataService):
    """
    Service for managing ratio-based data operations and technical indicator calculations.
    Specializes in financial ratio calculations and technical analysis.
    """
    
    def __init__(self,  database_service: Optional[DatabaseService] = None, db_type: str = 'sqlite',  scaler: str = 'standard'):
        """
        Initialize the ratio data service.
        
        Args:
            database_service: DatabaseService instance for data operations
            scaler: Scaling method for data normalization
        """
        super().__init__(database_service,db_type, scaler)

    def preprocess(self, data: pd.DataFrame, column_name: str) -> pd.DataFrame:
        """
        Preprocess the data with a focus on the specified column.
        
        Args:
            data: Input DataFrame
            column_name: Name of the column to preprocess
            
        Returns:
            Preprocessed DataFrame
        """
        if column_name not in data.columns:
            raise ValueError(f'The column {column_name} is missing in the data')

        # Convert column to numeric
        data[column_name] = pd.to_numeric(data[column_name], errors='coerce')
        return data

    def feature_engineering(self, data: pd.DataFrame, lookback: int = 30) -> pd.DataFrame:
        """
        Perform feature engineering on the data with rolling statistics.
        
        Args:
            data: Input DataFrame
            lookback: Window size for rolling calculations
            
        Returns:
            DataFrame with engineered features
        """
        price_col = 'price close'
        if price_col not in data.columns:
            raise ValueError(f"The '{price_col}' column is missing in the data.")

        # Calculate rolling statistics
        data['price_close_mean'] = data[price_col].rolling(window=lookback).mean()
        data['price_close_std'] = data[price_col].rolling(window=lookback).std()
        data['price_close_max'] = data[price_col].rolling(window=lookback).max()
        data['price_close_min'] = data[price_col].rolling(window=lookback).min()

        # Calculate percentage change
        data['price_close_pct_change'] = data[price_col].pct_change()

        # Drop rows with NaN values created by rolling calculations
        data = data.dropna()
        return data

    def _calc_normalised_returns(self, data: pd.DataFrame, column_name: str, 
                                window: int, freq: int) -> pd.Series:
        """
        Calculate normalized returns over a given window.
        
        Args:
            data: Input DataFrame
            column_name: Column name for calculations
            window: Rolling window size
            freq: Frequency for calculations
            
        Returns:
            Series with normalized returns
        """
        returns = self._calc_returns(data=data, column_name=column_name, period_offset=freq)
        std_return = self._calc_vol_series(data=returns, window=window)
        norm_returns = returns / (std_return * np.sqrt(freq))
        return norm_returns

    def add_deep_momentum_features(self, data: pd.DataFrame, column_name: str) -> pd.DataFrame:
        """
        Add Deep Momentum features to the data.
        
        Args:
            data: Input DataFrame
            column_name: Column name for calculations
            
        Returns:
            DataFrame with momentum features
        """
        data["daily_return"] = self._calc_returns(data=data, column_name=column_name, period_offset=1)
        data["daily_vol"] = self._calc_vol(data=data, column_name="daily_return", window=60)
        data["norm_daily_return"] = self._calc_normalised_returns(data=data, column_name=column_name, freq=1, window=60)
        data["norm_monthly_return"] = self._calc_normalised_returns(data=data, column_name=column_name, freq=21, window=60)
        data["norm_quarterly_return"] = self._calc_normalised_returns(data=data, column_name=column_name, freq=63, window=60)
        data["norm_biannual_return"] = self._calc_normalised_returns(data=data, column_name=column_name, freq=126, window=60)
        data["norm_annual_return"] = self._calc_normalised_returns(data=data, column_name=column_name, freq=252, window=60)
        return data

    def add_deep_momentum_feature(self, data: pd.DataFrame, column_name: str, period_offset: int) -> pd.DataFrame:
        """
        Add specific period momentum feature.
        
        Args:
            data: Input DataFrame
            column_name: Column name for calculations
            period_offset: Period for return calculation
            
        Returns:
            DataFrame with momentum feature
        """
        data[f"{period_offset}_period_offset_return"] = self._calc_returns(
            data=data, column_name=column_name, period_offset=period_offset
        )
        return data

    def add_macd_signal(self, data: pd.Series, short_window: int = 12, long_window: int = 26) -> pd.Series:
        """
        Calculate MACD signal indicator.
        
        Args:
            data: Price series
            short_window: Short EMA window
            long_window: Long EMA window
            
        Returns:
            MACD signal series
        """
        def _calc_halflife(timescale):
            return np.log(0.5) / (np.log(1 - 1 / timescale) + 1e-9)
            
        macd = (
            data.ewm(halflife=_calc_halflife(short_window)).mean()
            - data.ewm(halflife=_calc_halflife(long_window)).mean()
        )
        q = macd / (data.rolling(63).std().bfill() + 1e-9)
        return q / (q.rolling(252).std().bfill() + 1e-9)

    def add_macd_signal_features(self, data: pd.DataFrame, column_name: str) -> pd.DataFrame:
        """
        Add multiple MACD signal features with different timeframes.
        
        Args:
            data: Input DataFrame
            column_name: Column name for calculations
            
        Returns:
            DataFrame with MACD features
        """
        trend_combinations = [(8, 24), (16, 48), (32, 96)]
        for comb in trend_combinations:
            data[f'macd_{comb[0]}_{comb[1]}'] = self.add_macd_signal(
                data=data[column_name], short_window=comb[0], long_window=comb[1]
            )
        return data

    def add_target(self, data: pd.DataFrame, column_name: str, freq: int = 1) -> tuple:
        """
        Add volatility-scaled price return target.
        
        Args:
            data: Input DataFrame
            column_name: Column name for calculations
            freq: Trading frequency
            
        Returns:
            Tuple of (DataFrame with target, target column name)
        """
        data['target_returns'] = self._calc_vol_scaled_returns(
            data=data, column_name=column_name, period_offset=freq
        )
        data['target_returns'] = data['target_returns'].shift(-freq)
        return data, 'target_returns'

    def add_target_non_scaled(self, data: pd.DataFrame, column_name: str, freq: int = 1) -> tuple:
        """
        Add non-scaled price return target.
        
        Args:
            data: Input DataFrame
            column_name: Column name for calculations
            freq: Trading frequency
            
        Returns:
            Tuple of (DataFrame with target, target column name)
        """
        data['target_returns_nonscaled'] = self._calc_returns(
            data=data, column_name=column_name, period_offset=freq
        )
        data['target_returns_nonscaled'] = data['target_returns_nonscaled'].shift(-freq)
        return data, 'target_returns_nonscaled'

    def _calc_vol_scaled_returns(self, data: pd.DataFrame, column_name: str, period_offset=1):
        """Calculate volatility-scaled returns."""
        daily_vol = self._calc_vol(data, column_name, window=60)
        daily_returns = self._calc_returns(data, column_name, period_offset)
        annualized_vol = daily_vol * np.sqrt(252)
        return daily_returns * 0.15 / annualized_vol.shift(-1)

    def _calc_returns(self, data: pd.DataFrame, column_name: str, period_offset=1, log_transform=False):
        """Calculate returns (regular or log)."""
        if not log_transform:
            returns = data[column_name] / data[column_name].shift(period_offset) - 1.0
        else:
            returns = np.log(data[column_name]) - np.log(data[column_name].shift(period_offset).bfill())
        return returns

    def _calc_vol(self, data: pd.DataFrame, column_name: str, window=1):
        """Calculate volatility using exponential weighted standard deviation."""
        return data[column_name].ewm(span=window, min_periods=window).std().bfill()

    def _calc_vol_series(self, data: pd.Series, window=1):
        """Calculate volatility for a Series."""
        return data.ewm(span=window, min_periods=window).std().bfill()

    # === TECHNICAL INDICATOR METHODS ===

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-9)  # Add small value to avoid division by zero
        return 100 - (100 / (1 + rs))

    def calculate_stochastic_oscillator(self, high: pd.Series, low: pd.Series, close: pd.Series,
                                     k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator ratios."""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low + 1e-9))
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return {
            'k_percent': k_percent,
            'd_percent': d_percent
        }

    def calculate_macd_ratio(self, prices: pd.Series, fast_period: int = 12,
                           slow_period: int = 26, signal_period: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD ratio-based indicator."""
        fast_ema = prices.ewm(span=fast_period).mean()
        slow_ema = prices.ewm(span=slow_period).mean()
        
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal_period).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, 
                                std_dev: float = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands ratios."""
        rolling_mean = prices.rolling(window=period).mean()
        rolling_std = prices.rolling(window=period).std()
        
        upper = rolling_mean + (rolling_std * std_dev)
        lower = rolling_mean - (rolling_std * std_dev)
        
        return {
            'upper': upper,
            'lower': lower,
            'middle': rolling_mean,
            'bandwidth': (upper - lower) / (rolling_mean + 1e-9)
        }

    def add_rsi(self, data: pd.DataFrame, column_name: str, period: int = 14) -> pd.DataFrame:
        """Add RSI indicator using ratio-based calculation."""
        rsi_values = self.calculate_rsi(data[column_name], period)
        data[f'rsi_{period}'] = rsi_values
        return data

    def add_bollinger_bands(self, data: pd.DataFrame, column_name: str, 
                           period: int = 20, std_dev: float = 2) -> pd.DataFrame:
        """Add Bollinger Bands using ratio-based calculation."""
        bb_values = self.calculate_bollinger_bands(data[column_name], period, std_dev)
        
        data['bollinger_middle'] = bb_values['middle']
        data['bollinger_upper'] = bb_values['upper']
        data['bollinger_lower'] = bb_values['lower']
        data['bollinger_width'] = bb_values['upper'] - bb_values['lower']
        data['bollinger_position'] = (
            (data[column_name] - bb_values['lower']) / 
            (bb_values['upper'] - bb_values['lower'] + 1e-9)
        )
        return data

    def add_stochastic(self, data: pd.DataFrame, high_col: str, low_col: str, 
                      close_col: str, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
        """Add Stochastic Oscillator using ratio-based calculation."""
        if high_col not in data.columns or low_col not in data.columns:
            print(f"Warning: Required columns {high_col} or {low_col} not found. Using close price for approximation.")
            # Use close price with rolling min/max as approximation
            high_series = data[close_col].rolling(window=5).max()
            low_series = data[close_col].rolling(window=5).min()
        else:
            high_series = data[high_col]
            low_series = data[low_col]
            
        stoch_values = self.calculate_stochastic_oscillator(
            high_series, low_series, data[close_col], k_period, d_period
        )
        
        data['stoch_k'] = stoch_values['k_percent']
        data['stoch_d'] = stoch_values['d_percent']
        return data

    def add_all_technical_indicators(self, data: pd.DataFrame, price_col: str = 'price close',
                                   high_col: str = 'high', low_col: str = 'low') -> pd.DataFrame:
        """
        Add all available technical indicators to the DataFrame.
        
        Args:
            data: Input DataFrame
            price_col: Price column name
            high_col: High price column name
            low_col: Low price column name
            
        Returns:
            DataFrame with all technical indicators
        """
        # Add individual indicators
        data = self.add_rsi(data, price_col)
        data = self.add_bollinger_bands(data, price_col)
        data = self.add_macd_signal_features(data, price_col)
        data = self.add_deep_momentum_features(data, price_col)
        data = self.add_stochastic(data, high_col, low_col, price_col)
        
        # Add MACD
        macd_values = self.calculate_macd_ratio(data[price_col])
        data['macd'] = macd_values['macd']
        data['macd_signal'] = macd_values['signal']
        data['macd_histogram'] = macd_values['histogram']
        
        return data