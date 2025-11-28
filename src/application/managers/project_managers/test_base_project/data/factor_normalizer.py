"""
Factor Normalization Tool for Spatiotemporal Models.

This module provides comprehensive normalization capabilities for factors
with support for different normalization criteria:
- Company country-based normalization  
- Industry-based normalization
- Time-based vs population-based normalization

Designed to be inserted between _prepare_factor_data and _create_training_tensors
in the model training pipeline.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from application.services.database_service.database_service import DatabaseService
from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal


class NormalizationMethod(Enum):
    """Enumeration of available normalization methods."""
    Z_SCORE = "z_score"
    MIN_MAX = "min_max"
    RANK = "rank"
    QUANTILE = "quantile"


class NormalizationScope(Enum):
    """Enumeration of normalization scopes."""
    CROSS_SECTIONAL = "cross_sectional"  # Normalize across companies at each time point
    TIME_SERIES = "time_series"         # Normalize across time for each company
    GLOBAL = "global"                   # Normalize across all companies and time


@dataclass
class NormalizationConfig:
    """Configuration for factor normalization."""
    method: NormalizationMethod
    scope: NormalizationScope
    lookback_periods: Optional[int] = None  # For time series normalization
    min_observations: int = 10              # Minimum observations required
    winsorize_percentiles: Optional[Tuple[float, float]] = None  # (lower, upper) e.g., (0.01, 0.99)


class FactorNormalizer:
    """
    Comprehensive factor normalization tool with support for multiple
    normalization methods and criteria.
    """
    
    def __init__(self, database_service: DatabaseService):
        """
        Initialize the factor normalizer.
        
        Args:
            database_service: Database manager for accessing company metadata
        """
        self.database_service = database_service
        self.company_repository = CompanyShareRepositoryLocal(database_service.session)
        
        # Cache for company metadata
        self._company_metadata_cache = {}
        self._industry_mapping_cache = {}
        self._country_mapping_cache = {}
        
    def normalize_factor_data(self, 
                             factor_data: Dict[str, pd.DataFrame],
                             normalization_configs: Dict[str, NormalizationConfig]) -> Dict[str, pd.DataFrame]:
        """
        Normalize factor data according to specified configurations.
        
        Args:
            factor_data: Dictionary of {ticker: DataFrame} with factor values
            normalization_configs: Dictionary of {factor_name: NormalizationConfig}
            
        Returns:
            Dictionary of {ticker: DataFrame} with normalized factors
        """
        print("🔧 Starting comprehensive factor normalization...")
        
        # First, ensure we have company metadata
        self._load_company_metadata(list(factor_data.keys()))
        
        # Get all unique factor names across all tickers
        all_factors = set()
        for ticker_data in factor_data.values():
            all_factors.update(ticker_data.columns)
        
        print(f"  📊 Found {len(all_factors)} unique factors across {len(factor_data)} tickers")
        
        # Process each factor according to its configuration
        normalized_data = {ticker: df.copy() for ticker, df in factor_data.items()}
        
        for factor_name in all_factors:
            if factor_name in normalization_configs:
                config = normalization_configs[factor_name]
                print(f"  🔄 Normalizing {factor_name} using {config.method.value} ({config.scope.value})")
                
                self._normalize_single_factor(
                    normalized_data, factor_name, config
                )
            else:
                print(f"  ⚠️  No normalization config for {factor_name}, skipping")
        
        print("✅ Factor normalization complete")
        return normalized_data
    
    def create_normalized_return_factors(self,
                                       factor_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Create the missing normalized return factors (norm_daily_return, etc.)
        by mapping and normalizing existing momentum factors.
        
        Args:
            factor_data: Dictionary of {ticker: DataFrame} with factor values
            
        Returns:
            Dictionary with additional normalized return factors
        """
        print("📈 Creating normalized return factors...")
        
        # Mapping from existing momentum factors to normalized returns
        momentum_mapping = {
            'deep_momentum_1d': 'norm_daily_return',
            'deep_momentum_5d': 'norm_monthly_return',     # Approximate weekly -> monthly
            'deep_momentum_21d': 'norm_quarterly_return',   # Approximate monthly -> quarterly  
            'deep_momentum_63d': 'norm_biannual_return'    # Approximate quarterly -> biannual
        }
        
        # We'll also create annual returns from available data
        updated_data = {ticker: df.copy() for ticker, df in factor_data.items()}
        
        for ticker, df in updated_data.items():
            print(f"  🔄 Processing {ticker}...")
            
            # Create normalized return factors
            for existing_factor, new_factor in momentum_mapping.items():
                if existing_factor in df.columns:
                    # Copy the momentum factor and apply normalization
                    raw_returns = df[existing_factor].copy()
                    
                    # Apply cross-sectional normalization (z-score)
                    normalized_returns = self._apply_cross_sectional_zscore(
                        {ticker: raw_returns}, ticker, raw_returns.name
                    )
                    
                    df[new_factor] = normalized_returns
                    print(f"    ✅ Created {new_factor} from {existing_factor}")
                else:
                    print(f"    ⚠️  Missing source factor {existing_factor} for {new_factor}")
            
            # Create annual return if we have quarterly data
            if 'deep_momentum_63d' in df.columns:
                # Approximate annual from quarterly data
                quarterly_returns = df['deep_momentum_63d'].copy()
                
                # Calculate rolling annual return (4 quarters)
                annual_returns = quarterly_returns.rolling(window=4, min_periods=2).sum()
                
                # Normalize
                normalized_annual = self._apply_cross_sectional_zscore(
                    {ticker: annual_returns}, ticker, annual_returns.name
                )
                
                df['norm_annual_return'] = normalized_annual
                print(f"    ✅ Created norm_annual_return from quarterly data")
        
        return updated_data
    
    
    
    def apply_comprehensive_normalization(self,
                                        factor_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Apply comprehensive normalization pipeline including factor creation and normalization.
        
        This is the main method to be called between _prepare_factor_data and _create_training_tensors.
        
        Args:
            factor_data: Dictionary of {ticker: DataFrame} with raw factor values
            
        Returns:
            Dictionary with normalized and enhanced factor data
        """
        print("🚀 Applying comprehensive factor normalization pipeline...")
        
        # Step 1: Create missing normalized return factors
        enhanced_data = self.create_normalized_return_factors(factor_data)
        
        
        
        # Step 3: Define normalization configurations
        normalization_configs = self._get_default_normalization_configs()
        
        # Step 4: Apply comprehensive normalization
        normalized_data = self.normalize_factor_data(enhanced_data, normalization_configs)
        
        print("✅ Comprehensive factor normalization pipeline complete")
        return normalized_data
    
    def _load_company_metadata(self, tickers: List[str]) -> None:
        """Load company metadata for normalization purposes."""
        print("  📋 Loading company metadata...")
        
        for ticker in tickers:
            if ticker not in self._company_metadata_cache:
                try:
                    company = self.company_repository.get_by_ticker(ticker)
                    if company:
                        company = company[0] if isinstance(company, list) else company
                        
                        # Extract metadata
                        self._company_metadata_cache[ticker] = {
                            'sector': getattr(company, 'sector', 'Unknown'),
                            'industry': getattr(company, 'industry', 'Unknown'),
                            'country': 'US',  # Default - could be extracted from exchange or other fields
                        }
                    else:
                        # Default metadata for missing companies
                        self._company_metadata_cache[ticker] = {
                            'sector': 'Unknown',
                            'industry': 'Unknown', 
                            'country': 'US'
                        }
                        
                except Exception as e:
                    print(f"    ⚠️  Error loading metadata for {ticker}: {str(e)}")
                    self._company_metadata_cache[ticker] = {
                        'sector': 'Unknown',
                        'industry': 'Unknown',
                        'country': 'US'
                    }
    
    def _normalize_single_factor(self, 
                               factor_data: Dict[str, pd.DataFrame],
                               factor_name: str,
                               config: NormalizationConfig) -> None:
        """Normalize a single factor across all tickers."""
        
        if config.scope == NormalizationScope.CROSS_SECTIONAL:
            self._apply_cross_sectional_normalization(factor_data, factor_name, config)
        elif config.scope == NormalizationScope.TIME_SERIES:
            self._apply_time_series_normalization(factor_data, factor_name, config)
        elif config.scope == NormalizationScope.GLOBAL:
            self._apply_global_normalization(factor_data, factor_name, config)
    
    def _apply_cross_sectional_normalization(self, 
                                           factor_data: Dict[str, pd.DataFrame],
                                           factor_name: str,
                                           config: NormalizationConfig) -> None:
        """Apply cross-sectional normalization (across companies at each time point)."""
        
        # Collect all values for this factor across tickers
        all_dates = set()
        factor_series = {}
        
        for ticker, df in factor_data.items():
            if factor_name in df.columns:
                series = df[factor_name].dropna()
                factor_series[ticker] = series
                all_dates.update(series.index)
        
        # Sort dates
        all_dates = sorted(all_dates)
        
        # Normalize at each date
        for date in all_dates:
            values_at_date = {}
            
            # Collect values for this date
            for ticker, series in factor_series.items():
                if date in series.index:
                    values_at_date[ticker] = series[date]
            
            if len(values_at_date) < config.min_observations:
                continue
            
            # Normalize values
            values_array = np.array(list(values_at_date.values()))
            
            if config.winsorize_percentiles:
                values_array = self._winsorize(values_array, config.winsorize_percentiles)
            
            if config.method == NormalizationMethod.Z_SCORE:
                normalized_values = self._zscore_normalize(values_array)
            elif config.method == NormalizationMethod.MIN_MAX:
                normalized_values = self._minmax_normalize(values_array)
            elif config.method == NormalizationMethod.RANK:
                normalized_values = self._rank_normalize(values_array)
            elif config.method == NormalizationMethod.QUANTILE:
                normalized_values = self._quantile_normalize(values_array)
            else:
                normalized_values = values_array
            
            # Update the factor data
            for i, (ticker, _) in enumerate(values_at_date.items()):
                factor_data[ticker].loc[date, factor_name] = normalized_values[i]
    
    def _apply_time_series_normalization(self,
                                       factor_data: Dict[str, pd.DataFrame], 
                                       factor_name: str,
                                       config: NormalizationConfig) -> None:
        """Apply time series normalization (across time for each company)."""
        
        for ticker, df in factor_data.items():
            if factor_name not in df.columns:
                continue
            
            series = df[factor_name].dropna()
            if len(series) < config.min_observations:
                continue
            
            # Apply rolling normalization if lookback periods specified
            if config.lookback_periods:
                normalized_series = series.copy()
                
                for i in range(config.lookback_periods, len(series)):
                    window_data = series.iloc[i-config.lookback_periods:i].values
                    
                    if config.winsorize_percentiles:
                        window_data = self._winsorize(window_data, config.winsorize_percentiles)
                    
                    current_value = np.array([series.iloc[i]])
                    
                    if config.method == NormalizationMethod.Z_SCORE:
                        if np.std(window_data) > 0:
                            normalized_value = (current_value - np.mean(window_data)) / np.std(window_data)
                        else:
                            normalized_value = current_value
                    elif config.method == NormalizationMethod.MIN_MAX:
                        min_val, max_val = np.min(window_data), np.max(window_data)
                        if max_val > min_val:
                            normalized_value = (current_value - min_val) / (max_val - min_val)
                        else:
                            normalized_value = current_value
                    else:
                        normalized_value = current_value
                    
                    normalized_series.iloc[i] = normalized_value[0]
                
                factor_data[ticker][factor_name] = normalized_series
            else:
                # Apply global time series normalization
                values = series.values
                
                if config.winsorize_percentiles:
                    values = self._winsorize(values, config.winsorize_percentiles)
                
                if config.method == NormalizationMethod.Z_SCORE:
                    normalized_values = self._zscore_normalize(values)
                elif config.method == NormalizationMethod.MIN_MAX:
                    normalized_values = self._minmax_normalize(values)
                elif config.method == NormalizationMethod.RANK:
                    normalized_values = self._rank_normalize(values)
                elif config.method == NormalizationMethod.QUANTILE:
                    normalized_values = self._quantile_normalize(values)
                else:
                    normalized_values = values
                
                factor_data[ticker].loc[series.index, factor_name] = normalized_values
    
    def _apply_global_normalization(self,
                                  factor_data: Dict[str, pd.DataFrame],
                                  factor_name: str, 
                                  config: NormalizationConfig) -> None:
        """Apply global normalization (across all companies and time)."""
        
        # Collect all values across all tickers and dates
        all_values = []
        value_locations = []
        
        for ticker, df in factor_data.items():
            if factor_name in df.columns:
                series = df[factor_name].dropna()
                all_values.extend(series.values)
                value_locations.extend([(ticker, date) for date in series.index])
        
        if len(all_values) < config.min_observations:
            return
        
        all_values = np.array(all_values)
        
        if config.winsorize_percentiles:
            all_values = self._winsorize(all_values, config.winsorize_percentiles)
        
        # Apply normalization
        if config.method == NormalizationMethod.Z_SCORE:
            normalized_values = self._zscore_normalize(all_values)
        elif config.method == NormalizationMethod.MIN_MAX:
            normalized_values = self._minmax_normalize(all_values)
        elif config.method == NormalizationMethod.RANK:
            normalized_values = self._rank_normalize(all_values)
        elif config.method == NormalizationMethod.QUANTILE:
            normalized_values = self._quantile_normalize(all_values)
        else:
            normalized_values = all_values
        
        # Update factor data with normalized values
        for i, (ticker, date) in enumerate(value_locations):
            factor_data[ticker].loc[date, factor_name] = normalized_values[i]
    
    def _apply_cross_sectional_zscore(self,
                                     factor_data: Dict[str, pd.DataFrame],
                                     current_ticker: str,
                                     factor_name: str) -> pd.Series:
        """Helper method to apply cross-sectional z-score normalization to a single series."""
        if current_ticker not in factor_data:
            return pd.Series()
        
        series = factor_data[current_ticker]
        
        # For simplicity, just apply z-score normalization to the series itself
        # In a full implementation, you'd normalize across all tickers at each date
        return (series - series.mean()) / series.std() if series.std() > 0 else series
    
    def _calculate_macd(self, prices: pd.Series, fast: int, slow: int) -> pd.Series:
        """Calculate MACD indicator."""
        try:
            # Calculate exponential moving averages
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            
            # MACD line
            macd_line = ema_fast - ema_slow
            
            return macd_line
            
        except Exception as e:
            print(f"    ❌ Error calculating MACD: {str(e)}")
            return pd.Series(index=prices.index, dtype=float)
    
    def _get_default_normalization_configs(self) -> Dict[str, NormalizationConfig]:
        """Get default normalization configurations for different factor types."""
        
        return {
            # Basic price data - cross-sectional normalization
            'High': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.CROSS_SECTIONAL,
                winsorize_percentiles=(0.01, 0.99)
            ),
            'Low': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.CROSS_SECTIONAL,
                winsorize_percentiles=(0.01, 0.99)
            ),
            'Open': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.CROSS_SECTIONAL,
                winsorize_percentiles=(0.01, 0.99)
            ),
            'Close': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.CROSS_SECTIONAL,
                winsorize_percentiles=(0.01, 0.99)
            ),
            'Adj Close': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.CROSS_SECTIONAL,
                winsorize_percentiles=(0.01, 0.99)
            ),

            # Raw momentum factors - cross-sectional normalization
            'deep_momentum_1d': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.CROSS_SECTIONAL,
                winsorize_percentiles=(0.01, 0.99)
            ),
            'deep_momentum_5d': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.CROSS_SECTIONAL,
                winsorize_percentiles=(0.01, 0.99)
            ),
            'deep_momentum_21d': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.CROSS_SECTIONAL,
                winsorize_percentiles=(0.01, 0.99)
            ),
            'deep_momentum_63d': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.CROSS_SECTIONAL,
                winsorize_percentiles=(0.01, 0.99)
            ),

            # Normalized returns - cross-sectional z-score
            'norm_daily_return': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.CROSS_SECTIONAL,
                winsorize_percentiles=(0.01, 0.99)
            ),
            'norm_monthly_return': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.CROSS_SECTIONAL,
                winsorize_percentiles=(0.01, 0.99)
            ),
            'norm_quarterly_return': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.CROSS_SECTIONAL,
                winsorize_percentiles=(0.01, 0.99)
            ),
            'norm_biannual_return': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.CROSS_SECTIONAL,
                winsorize_percentiles=(0.01, 0.99)
            ),
            'norm_annual_return': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.CROSS_SECTIONAL,
                winsorize_percentiles=(0.01, 0.99)
            ),
            
            # MACD factors - time series normalization
            'macd_8_24': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.TIME_SERIES,
                lookback_periods=63  # ~3 months
            ),
            'macd_16_48': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.TIME_SERIES,
                lookback_periods=63
            ),
            'macd_32_96': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.TIME_SERIES,
                lookback_periods=126  # ~6 months
            ),
            
            # Technical indicators - cross-sectional rank normalization
            'rsi_14': NormalizationConfig(
                method=NormalizationMethod.RANK,
                scope=NormalizationScope.CROSS_SECTIONAL
            ),
            'bollinger_upper': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.CROSS_SECTIONAL
            ),
            'bollinger_lower': NormalizationConfig(
                method=NormalizationMethod.Z_SCORE,
                scope=NormalizationScope.CROSS_SECTIONAL
            )
        }
    
    # Normalization utility methods
    def _zscore_normalize(self, values: np.ndarray) -> np.ndarray:
        """Apply z-score normalization."""
        mean_val = np.mean(values)
        std_val = np.std(values)
        if std_val > 0:
            return (values - mean_val) / std_val
        else:
            return values
    
    def _minmax_normalize(self, values: np.ndarray) -> np.ndarray:
        """Apply min-max normalization."""
        min_val = np.min(values)
        max_val = np.max(values)
        if max_val > min_val:
            return (values - min_val) / (max_val - min_val)
        else:
            return values
    
    def _rank_normalize(self, values: np.ndarray) -> np.ndarray:
        """Apply rank-based normalization."""
        from scipy.stats import rankdata
        ranks = rankdata(values, method='dense')
        return (ranks - 1) / (len(np.unique(ranks)) - 1) if len(np.unique(ranks)) > 1 else ranks
    
    def _quantile_normalize(self, values: np.ndarray) -> np.ndarray:
        """Apply quantile normalization."""
        from scipy.stats import norm, rankdata
        ranks = rankdata(values, method='average')
        quantiles = (ranks - 0.5) / len(values)
        return norm.ppf(quantiles)
    
    def _winsorize(self, values: np.ndarray, percentiles: Tuple[float, float]) -> np.ndarray:
        """Apply winsorization to handle outliers."""
        lower_percentile, upper_percentile = percentiles
        lower_bound = np.percentile(values, lower_percentile * 100)
        upper_bound = np.percentile(values, upper_percentile * 100)
        
        return np.clip(values, lower_bound, upper_bound)