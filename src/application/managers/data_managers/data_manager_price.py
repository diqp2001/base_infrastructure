import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from src.application.managers.data_managers.data_manager import DataManager

class DataManagerPrice(DataManager):
    def __init__(self, database_manager, scaler: str = 'standard'):
        super().__init__(database_manager, scaler)

    def preprocess(self, data: pd.DataFrame, column_name: str) -> pd.DataFrame:
        """
        Preprocess the data with a focus on the 'price close' column.
        """
        # Ensure the 'price close' column is present
        if column_name not in data.columns:
            raise ValueError(f'The column {column_name} is missing in the data')
        

        # Convert 'price close' to numeric
        data[column_name] = pd.to_numeric(data[column_name], errors='coerce')

        return data

    def feature_engineering(self, data: pd.DataFrame, lookback: int = 30) -> pd.DataFrame:
        """
        Perform feature engineering on the data with a focus on the 'price close' column.
        """
        # Ensure the 'price close' column is present
        if 'price close' not in data.columns:
            raise ValueError("The 'price close' column is missing in the data.")

        # Calculate rolling statistics
        data['price_close_mean'] = data['price close'].rolling(window=lookback).mean()
        data['price_close_std'] = data['price close'].rolling(window=lookback).std()
        data['price_close_max'] = data['price close'].rolling(window=lookback).max()
        data['price_close_min'] = data['price close'].rolling(window=lookback).min()

        # Calculate percentage change
        data['price_close_pct_change'] = data['price close'].pct_change()

        # Drop rows with NaN values created by rolling calculations
        data = data.dropna()

        return data

    def _calc_normalised_returns(self, data: pd.DataFrame, column_name: str, window: int, freq: int) -> pd.Series:
        """
        Calculate normalized returns over a given window.
        """
        returns = self._calc_returns(data= data, column_name= column_name, period_offset=freq)
        std_return = self._calc_vol_series(data= returns, window= window)
        norm_returns = (returns) / (std_return * np.sqrt(freq))
        return norm_returns

    def add_deep_momentum_features(self, data: pd.DataFrame, column_name: str) -> pd.DataFrame:
        """
        Add Deep Momentum features to the data.
        """
        data["daily_return"] = self._calc_returns(data= data, column_name= column_name, period_offset=1)
        data["daily_vol"] = self._calc_vol(data= data, column_name= "daily_return", window=60)
        data["norm_daily_return"] = self._calc_normalised_returns(data= data,column_name= column_name, freq=1, window=60)
        data["norm_monthly_return"] = self._calc_normalised_returns(data= data,column_name= column_name, freq=21, window=60)
        data["norm_quarterly_return"] = self._calc_normalised_returns(data= data,column_name= column_name, freq=63, window=60)
        data["norm_biannual_return"] = self._calc_normalised_returns(data= data,column_name= column_name, freq=126, window=60)
        data["norm_annual_return"] = self._calc_normalised_returns(data= data,column_name= column_name, freq=252, window=60)

        return data
    def add_deep_momentum_feature(self, data: pd.DataFrame, column_name: str, period_offset: int) -> pd.DataFrame:
        """
        Add Deep Momentum features to the data.
        """
        data[f"{period_offset}_period_offset_return"] = self._calc_returns(data= data, column_name= column_name, period_offset=period_offset)
        

        return data
    
    def add_macd_signal(self, data: pd.Series, short_window: int = 12, long_window: int =26) -> pd.Series:

        def _calc_halflife(timescale):
            return np.log(0.5) /(np.log(1 - 1 / timescale) + 1e-9)
        macd = (
            data.ewm(halflife= _calc_halflife(short_window)).mean()
            - data.ewm(halflife= _calc_halflife(long_window)).mean()
        )
        q = macd / (data.rolling(63).std().bfill() + 1e-9)

        return q / (q.rolling(252).std().bfill() + 1e-9)

    def add_macd_signal_features(self, data: pd.DataFrame, column_name: str) -> pd.DataFrame:
        trend_combinations = [(8,24),(16,48),(32,96)]
        for comb in trend_combinations:
            data[f'macd_{comb[0]}_{comb[1]}'] = self.add_macd_signal(data= data[column_name], short_window= comb[0], long_window= comb[1])
        return data

    def add_macd_features(self, data: pd.DataFrame, short_window: int = 12, long_window: int = 26, signal_window: int = 9) -> pd.DataFrame:
        """
        Add MACD (Moving Average Convergence Divergence) features to the data.
        """
        # Calculate short-term and long-term exponential moving averages
        short_ema = data['price close'].ewm(span=short_window, adjust=False).mean()
        long_ema = data['price close'].ewm(span=long_window, adjust=False).mean()

        # Calculate MACD and signal line
        data['macd'] = short_ema - long_ema
        data['macd_signal'] = data['macd'].ewm(span=signal_window, adjust=False).mean()

        # Calculate MACD histogram
        data['macd_histogram'] = data['macd'] - data['macd_signal']

        return data
    
    def add_target(self, data:pd.DataFrame, column_name: str, freq: int=1)-> pd.DataFrame:
        """
        Add price return target based on freq on trading
        """

        data['target_returns'] = self._calc_vol_scaled_returns(data= data, column_name= column_name, period_offset=freq)
        data['target_returns'] = data['target_returns'].shift(-freq)
        target_column_name = 'target_returns'
        return data, target_column_name
    
    def add_target_non_scaled(self, data:pd.DataFrame, column_name: str, freq: int=1)-> pd.DataFrame:
        """
        Add price return target based on freq on trading
        """

        data['target_returns_nonscaled'] = self._calc_returns(data= data, column_name= column_name, period_offset=freq)
        data['target_returns_nonscaled'] = data['target_returns'].shift(-freq)
        target_column_name = 'target_returns_nonscaled'
        return data, target_column_name
    
    def _calc_vol_scaled_returns(self, data: pd.DataFrame, column_name: str, period_offset=1):
        daily_vol = self._calc_vol(data, column_name, window=60)
        daily_returns = self._calc_returns(data, column_name, period_offset)
        annualized_vol = daily_vol*np.sqrt(252)
        return daily_returns * 0.15 / annualized_vol.shift(-1)
    
    def _calc_returns(self, data: pd.DataFrame, column_name: str, period_offset=1, log_transform=False):
        if not log_transform:
            returns = data[column_name] / data[column_name].shift(period_offset) - 1.0
        else:
            returns = np.log(data[column_name]) - np.log(data[column_name].shift(period_offset).bfill())

        return returns
    
    def _calc_vol(self, data: pd.DataFrame, column_name: str, window=1):
        s = data[column_name].ewm(span=window, min_periods=window).std().bfill()
        return s
    
    def _calc_vol_series(self, data:pd.Series, window=1):
        s = data.ewm(span=window, min_periods=window).std().bfill()
        return s