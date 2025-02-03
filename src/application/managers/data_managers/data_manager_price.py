import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from src.application.managers.data_managers.data_manager import DataManager

class DataManagerPrice(DataManager):
    def __init__(self):
        super().__init__()

    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess the data with a focus on the 'price close' column.
        """
        # Ensure the 'price close' column is present
        if 'price close' not in data.columns:
            raise ValueError("The 'price close' column is missing in the data.")

        # Drop missing values
        data = data.dropna(subset=['price close'])

        # Convert 'price close' to numeric
        data['price close'] = pd.to_numeric(data['price close'], errors='coerce')

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

    def _calc_normalised_returns(self, data: pd.DataFrame, window: int) -> pd.Series:
        """
        Calculate normalized returns over a given window.
        """
        returns = data['price close'].pct_change(window)
        mean_return = returns.rolling(window=window).mean()
        std_return = returns.rolling(window=window).std()
        norm_returns = (returns - mean_return) / std_return
        return norm_returns

    def add_deep_momentum_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Add Deep Momentum features to the data.
        """
        data["norm_daily_return"] = self._calc_normalised_returns(data, 1)
        data["norm_monthly_return"] = self._calc_normalised_returns(data, 21)
        data["norm_quarterly_return"] = self._calc_normalised_returns(data, 63)
        data["norm_biannual_return"] = self._calc_normalised_returns(data, 126)
        data["norm_annual_return"] = self._calc_normalised_returns(data, 252)

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