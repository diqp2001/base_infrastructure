"""
Simple 200-day moving average signal generation for trading strategies.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..config import DEFAULT_CONFIG


class SimpleSignalGenerator:
    """Generates simple binary trading signals from 200-day moving averages."""
    
    def __init__(self, moving_average_window: int = 200):
        self.moving_average_window = moving_average_window
        self.config = DEFAULT_CONFIG
    
    def generate_trading_signals(self,
                               price_data: pd.DataFrame,
                               price_column: str = 'close') -> Dict[str, int]:
        """Generate trading signals from price data using 200-day moving average.
        
        Args:
            price_data: DataFrame with price data
            price_column: Column name containing price data
            
        Returns:
            Dictionary with ticker -> signal mapping (1=long, -1=short)
        """
        signals = {}
        
        if price_column not in price_data.columns:
            return signals
            
        # Calculate 200-day moving average
        price_data['ma_200'] = price_data[price_column].rolling(window=self.moving_average_window).mean()
        
        # Generate signals: 1 if price > MA, -1 if price < MA
        latest_price = price_data[price_column].iloc[-1]
        latest_ma = price_data['ma_200'].iloc[-1]
        
        if pd.notna(latest_ma) and pd.notna(latest_price):
            signal = 1 if latest_price > latest_ma else -1
            # Assuming single ticker data - use a generic key or extract from data
            signals['signal'] = signal
            
        return signals
    
    def get_signal_confidence(self, signals: Dict[str, int]) -> Dict[str, float]:
        """Get signal confidence - always 1.0 for simple binary signals."""
        return {ticker: 1.0 for ticker in signals.keys()}
    
    def calculate_200_day_average(self, prices: pd.Series) -> float:
        """Calculate 200-day simple moving average."""
        if len(prices) < self.moving_average_window:
            return np.nan
        return prices.tail(self.moving_average_window).mean()
    
    def generate_signal_for_ticker(self, current_price: float, moving_average: float) -> int:
        """Generate binary signal for a single ticker.
        
        Args:
            current_price: Current closing price
            moving_average: 200-day moving average
            
        Returns:
            1 for long, -1 for short
        """
        if pd.isna(current_price) or pd.isna(moving_average):
            return 0  # No signal if data is missing
        
        return 1 if current_price > moving_average else -1