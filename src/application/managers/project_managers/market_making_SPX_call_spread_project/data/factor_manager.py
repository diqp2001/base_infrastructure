"""
SPX Factor Manager for Market Making Call Spread Project

This module manages factor creation and storage for SPX index data,
following the pattern from test_base_project factor management.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from src.application.services.database_service.database_service import DatabaseService

logger = logging.getLogger(__name__)


class SPXFactorManager:
    """
    Factor manager for SPX market making strategies.
    Handles creation, calculation, and storage of factors related to SPX trading.
    """
    
    def __init__(self, database_service: DatabaseService):
        """
        Initialize the SPX factor manager.
        
        Args:
            database_service: Database service instance
        """
        self.database_service = database_service
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def create_spx_price_factors(self, spx_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Create basic price factors for SPX.
        
        Args:
            spx_data: DataFrame containing SPX OHLCV data
            
        Returns:
            Dict containing factor creation results
        """
        self.logger.info("Creating SPX price factors...")
        
        try:
            factors_created = []
            
            # Basic OHLCV factors
            basic_factors = {
                'spx_open': spx_data['open'],
                'spx_high': spx_data['high'], 
                'spx_low': spx_data['low'],
                'spx_close': spx_data['close'],
                'spx_volume': spx_data['volume'],
            }
            
            # Price-derived factors
            derived_factors = {
                'spx_typical_price': (spx_data['high'] + spx_data['low'] + spx_data['close']) / 3,
                'spx_hl_spread': spx_data['high'] - spx_data['low'],
                'spx_oc_spread': spx_data['open'] - spx_data['close'],
                'spx_price_change': spx_data['close'].pct_change(),
                'spx_log_return': np.log(spx_data['close'] / spx_data['close'].shift(1)),
            }
            
            all_factors = {**basic_factors, **derived_factors}
            factors_created.extend(all_factors.keys())
            
            # Store factors in database (implement based on your factor system)
            stored_count = self._store_factors(all_factors)
            
            result = {
                'success': True,
                'factors_created': factors_created,
                'factors_stored': stored_count,
                'timestamp': datetime.now().isoformat(),
            }
            
            self.logger.info(f"✅ Created {len(factors_created)} SPX price factors")
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating SPX price factors: {e}")
            return {
                'success': False,
                'error': str(e),
                'factors_created': [],
                'timestamp': datetime.now().isoformat(),
            }
    
    def create_spx_technical_factors(self, spx_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Create technical indicator factors for SPX.
        
        Args:
            spx_data: DataFrame containing SPX OHLCV data
            
        Returns:
            Dict containing factor creation results
        """
        self.logger.info("Creating SPX technical factors...")
        
        try:
            factors_created = []
            
            # Moving averages
            ma_factors = {
                'spx_sma_10': spx_data['close'].rolling(window=10).mean(),
                'spx_sma_20': spx_data['close'].rolling(window=20).mean(),
                'spx_sma_50': spx_data['close'].rolling(window=50).mean(),
                'spx_ema_10': spx_data['close'].ewm(span=10).mean(),
                'spx_ema_20': spx_data['close'].ewm(span=20).mean(),
            }
            
            # RSI
            rsi_factors = self._calculate_rsi(spx_data['close'])
            
            # MACD
            macd_factors = self._calculate_macd(spx_data['close'])
            
            # Bollinger Bands
            bb_factors = self._calculate_bollinger_bands(spx_data['close'])
            
            # Volatility indicators
            vol_factors = {
                'spx_realized_vol_10': spx_data['close'].pct_change().rolling(window=10).std() * np.sqrt(252),
                'spx_realized_vol_20': spx_data['close'].pct_change().rolling(window=20).std() * np.sqrt(252),
                'spx_atr_14': self._calculate_atr(spx_data),
            }
            
            all_factors = {**ma_factors, **rsi_factors, **macd_factors, **bb_factors, **vol_factors}
            factors_created.extend(all_factors.keys())
            
            # Store factors in database
            stored_count = self._store_factors(all_factors)
            
            result = {
                'success': True,
                'factors_created': factors_created,
                'factors_stored': stored_count,
                'timestamp': datetime.now().isoformat(),
            }
            
            self.logger.info(f"✅ Created {len(factors_created)} SPX technical factors")
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating SPX technical factors: {e}")
            return {
                'success': False,
                'error': str(e),
                'factors_created': [],
                'timestamp': datetime.now().isoformat(),
            }
    
    def create_spx_volatility_factors(self, spx_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Create volatility-specific factors for SPX options trading.
        
        Args:
            spx_data: DataFrame containing SPX OHLCV data
            
        Returns:
            Dict containing factor creation results
        """
        self.logger.info("Creating SPX volatility factors...")
        
        try:
            factors_created = []
            
            # Returns for volatility calculation
            returns = spx_data['close'].pct_change()
            log_returns = np.log(spx_data['close'] / spx_data['close'].shift(1))
            
            # Historical volatility factors
            vol_factors = {
                'spx_hv_5': returns.rolling(window=5).std() * np.sqrt(252),
                'spx_hv_10': returns.rolling(window=10).std() * np.sqrt(252),
                'spx_hv_20': returns.rolling(window=20).std() * np.sqrt(252),
                'spx_hv_30': returns.rolling(window=30).std() * np.sqrt(252),
                'spx_hv_60': returns.rolling(window=60).std() * np.sqrt(252),
            }
            
            # Volatility ratios
            ratio_factors = {
                'spx_hv_ratio_20_5': vol_factors['spx_hv_20'] / vol_factors['spx_hv_5'],
                'spx_hv_ratio_30_10': vol_factors['spx_hv_30'] / vol_factors['spx_hv_10'],
            }
            
            # Volatility clustering indicators
            cluster_factors = {
                'spx_vol_cluster': returns.rolling(window=5).std().rolling(window=20).std(),
                'spx_garch_proxy': returns.abs().rolling(window=20).mean(),
            }
            
            # Range-based volatility (Garman-Klass)
            gk_vol = self._calculate_garman_klass_volatility(spx_data)
            range_factors = {
                'spx_gk_volatility': gk_vol,
                'spx_range_ratio': (spx_data['high'] - spx_data['low']) / spx_data['close'],
            }
            
            all_factors = {**vol_factors, **ratio_factors, **cluster_factors, **range_factors}
            factors_created.extend(all_factors.keys())
            
            # Store factors in database
            stored_count = self._store_factors(all_factors)
            
            result = {
                'success': True,
                'factors_created': factors_created,
                'factors_stored': stored_count,
                'timestamp': datetime.now().isoformat(),
            }
            
            self.logger.info(f"✅ Created {len(factors_created)} SPX volatility factors")
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating SPX volatility factors: {e}")
            return {
                'success': False,
                'error': str(e),
                'factors_created': [],
                'timestamp': datetime.now().isoformat(),
            }
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> Dict[str, pd.Series]:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return {'spx_rsi_14': rsi}
    
    def _calculate_macd(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """Calculate MACD indicator."""
        ema_12 = prices.ewm(span=12).mean()
        ema_26 = prices.ewm(span=26).mean()
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9).mean()
        histogram = macd_line - signal_line
        
        return {
            'spx_macd_line': macd_line,
            'spx_macd_signal': signal_line,
            'spx_macd_histogram': histogram,
        }
    
    def _calculate_bollinger_bands(self, prices: pd.Series, window: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands."""
        ma = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        upper = ma + (std * std_dev)
        lower = ma - (std * std_dev)
        
        return {
            'spx_bb_upper': upper,
            'spx_bb_middle': ma,
            'spx_bb_lower': lower,
            'spx_bb_width': upper - lower,
            'spx_bb_position': (prices - lower) / (upper - lower),
        }
    
    def _calculate_atr(self, ohlc_data: pd.DataFrame, window: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        tr1 = ohlc_data['high'] - ohlc_data['low']
        tr2 = abs(ohlc_data['high'] - ohlc_data['close'].shift(1))
        tr3 = abs(ohlc_data['low'] - ohlc_data['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=window).mean()
    
    def _calculate_garman_klass_volatility(self, ohlc_data: pd.DataFrame, window: int = 20) -> pd.Series:
        """Calculate Garman-Klass volatility estimator."""
        log_hl = np.log(ohlc_data['high'] / ohlc_data['low'])
        log_co = np.log(ohlc_data['close'] / ohlc_data['open'])
        gk = 0.5 * log_hl**2 - (2*np.log(2)-1) * log_co**2
        return np.sqrt(gk.rolling(window=window).mean() * 252)
    
    def _store_factors(self, factors: Dict[str, pd.Series]) -> int:
        """
        Store factors in database using the factor system.
        
        Args:
            factors: Dictionary of factor name -> values
            
        Returns:
            Number of factors stored
        """
        # TODO: Implement actual database storage using factor system
        # This would involve:
        # 1. Creating factor definitions if they don't exist
        # 2. Storing factor values
        
        self.logger.info(f"Storing {len(factors)} factors in database...")
        return len(factors)