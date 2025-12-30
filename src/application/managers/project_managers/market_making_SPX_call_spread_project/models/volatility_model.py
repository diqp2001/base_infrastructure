"""
Volatility Model for SPX Options Market Making

This module implements various volatility models for SPX options,
including implied volatility surface modeling and volatility forecasting.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from scipy.interpolate import griddata, RBFInterpolator
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor

logger = logging.getLogger(__name__)


class VolatilityModel:
    """
    Volatility modeling for SPX options market making.
    Handles implied volatility surface construction and volatility forecasting.
    """
    
    def __init__(self):
        """Initialize the volatility model."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.iv_surface = None
        self.scaler = StandardScaler()
        self.vol_forecast_model = None
    
    def build_implied_volatility_surface(
        self,
        option_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build implied volatility surface from option market data.
        
        Args:
            option_data: List of option data with strike, expiry, IV, etc.
            
        Returns:
            Dict containing volatility surface data
        """
        try:
            if not option_data:
                raise ValueError("No option data provided")
            
            # Convert to DataFrame
            df = pd.DataFrame(option_data)
            
            # Calculate moneyness and time to expiry
            df['moneyness'] = df['strike'] / df['underlying_price']
            df['tte'] = (pd.to_datetime(df['expiry']) - datetime.now()).dt.days / 365.25
            
            # Filter for valid data
            df = df[
                (df['implied_volatility'] > 0.05) &  # Min IV 5%
                (df['implied_volatility'] < 2.0) &   # Max IV 200%
                (df['tte'] > 0) &                    # Future expiry
                (df['tte'] < 2.0) &                  # Max 2 years
                (df['moneyness'] > 0.5) &            # Deep OTM filter
                (df['moneyness'] < 2.0)              # Deep ITM filter
            ].copy()
            
            if len(df) < 10:
                raise ValueError("Insufficient valid option data for surface construction")
            
            # Create volatility surface using interpolation
            moneyness_grid = np.linspace(0.7, 1.3, 50)
            tte_grid = np.linspace(0.02, 1.0, 50)
            moneyness_mesh, tte_mesh = np.meshgrid(moneyness_grid, tte_grid)
            
            # Interpolate implied volatility
            points = df[['moneyness', 'tte']].values
            values = df['implied_volatility'].values
            
            # Use RBF interpolation for smoother surface
            iv_interpolated = griddata(
                points,
                values,
                (moneyness_mesh, tte_mesh),
                method='cubic',
                fill_value=np.nan
            )
            
            # Fill NaN values with linear interpolation
            mask = np.isnan(iv_interpolated)
            iv_interpolated_linear = griddata(
                points,
                values,
                (moneyness_mesh, tte_mesh),
                method='linear',
                fill_value=0.2  # Default volatility
            )
            iv_interpolated[mask] = iv_interpolated_linear[mask]
            
            # Store surface data
            self.iv_surface = {
                'moneyness_grid': moneyness_grid,
                'tte_grid': tte_grid,
                'iv_surface': iv_interpolated,
                'raw_data': df,
                'created_at': datetime.now(),
            }
            
            # Calculate surface statistics
            surface_stats = self._calculate_surface_statistics(df)
            
            return {
                'success': True,
                'surface_points': len(df),
                'moneyness_range': (df['moneyness'].min(), df['moneyness'].max()),
                'tte_range': (df['tte'].min(), df['tte'].max()),
                'iv_range': (df['implied_volatility'].min(), df['implied_volatility'].max()),
                'surface_stats': surface_stats,
                'created_at': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error building implied volatility surface: {e}")
            return {
                'success': False,
                'error': str(e),
                'surface_points': 0,
            }
    
    def get_implied_volatility(
        self,
        strike: float,
        underlying_price: float,
        time_to_expiry: float
    ) -> float:
        """
        Get implied volatility from surface for given strike and time to expiry.
        
        Args:
            strike: Option strike price
            underlying_price: Current underlying price
            time_to_expiry: Time to expiry in years
            
        Returns:
            Implied volatility
        """
        try:
            if self.iv_surface is None:
                self.logger.warning("No volatility surface available, using default")
                return 0.20  # Default 20% volatility
            
            moneyness = strike / underlying_price
            
            # Interpolate from surface
            moneyness_grid = self.iv_surface['moneyness_grid']
            tte_grid = self.iv_surface['tte_grid']
            iv_surface = self.iv_surface['iv_surface']
            
            # Find nearest grid points
            mon_idx = np.searchsorted(moneyness_grid, moneyness)
            tte_idx = np.searchsorted(tte_grid, time_to_expiry)
            
            # Ensure indices are within bounds
            mon_idx = max(0, min(len(moneyness_grid) - 1, mon_idx))
            tte_idx = max(0, min(len(tte_grid) - 1, tte_idx))
            
            # Get IV from surface
            iv = iv_surface[tte_idx, mon_idx]
            
            # Handle NaN or invalid values
            if np.isnan(iv) or iv <= 0:
                # Use nearest valid point or default
                iv = self._get_nearest_valid_iv(moneyness, time_to_expiry)
            
            return max(0.05, min(2.0, iv))  # Bound between 5% and 200%
            
        except Exception as e:
            self.logger.error(f"Error getting implied volatility: {e}")
            return 0.20  # Default volatility
    
    def calculate_volatility_skew(
        self,
        time_to_expiry: float,
        underlying_price: float
    ) -> Dict[str, Any]:
        """
        Calculate volatility skew for a given expiry.
        
        Args:
            time_to_expiry: Time to expiry in years
            underlying_price: Current underlying price
            
        Returns:
            Dict containing skew analysis
        """
        try:
            if self.iv_surface is None:
                raise ValueError("No volatility surface available")
            
            # Generate moneyness range
            moneyness_range = np.linspace(0.8, 1.2, 41)
            strikes = moneyness_range * underlying_price
            
            # Get IV for each strike
            ivs = [
                self.get_implied_volatility(strike, underlying_price, time_to_expiry)
                for strike in strikes
            ]
            
            # Calculate skew metrics
            atm_iv = self.get_implied_volatility(underlying_price, underlying_price, time_to_expiry)
            otm_put_iv = self.get_implied_volatility(underlying_price * 0.9, underlying_price, time_to_expiry)
            otm_call_iv = self.get_implied_volatility(underlying_price * 1.1, underlying_price, time_to_expiry)
            
            put_skew = otm_put_iv - atm_iv
            call_skew = otm_call_iv - atm_iv
            skew_ratio = put_skew / call_skew if call_skew != 0 else 0
            
            # Calculate slope of skew
            skew_slope = np.polyfit(moneyness_range, ivs, 1)[0]
            
            return {
                'time_to_expiry': time_to_expiry,
                'atm_iv': atm_iv,
                'otm_put_iv': otm_put_iv,
                'otm_call_iv': otm_call_iv,
                'put_skew': put_skew,
                'call_skew': call_skew,
                'skew_ratio': skew_ratio,
                'skew_slope': skew_slope,
                'moneyness_range': moneyness_range.tolist(),
                'iv_curve': ivs,
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility skew: {e}")
            return {
                'error': str(e),
                'time_to_expiry': time_to_expiry,
            }
    
    def forecast_volatility(
        self,
        historical_data: pd.DataFrame,
        forecast_horizon: int = 20
    ) -> Dict[str, Any]:
        """
        Forecast future volatility using historical data.
        
        Args:
            historical_data: DataFrame with OHLCV data
            forecast_horizon: Number of days to forecast
            
        Returns:
            Dict containing volatility forecast
        """
        try:
            # Calculate realized volatility
            returns = historical_data['close'].pct_change().dropna()
            
            # Calculate rolling volatilities
            vol_windows = [5, 10, 20, 30, 60]
            vol_features = {}
            
            for window in vol_windows:
                vol_features[f'rv_{window}'] = returns.rolling(window).std() * np.sqrt(252)
            
            # Add additional features
            vol_features['returns'] = returns
            vol_features['abs_returns'] = returns.abs()
            vol_features['squared_returns'] = returns ** 2
            vol_features['log_vol'] = np.log(vol_features['rv_20'] + 1e-8)
            
            # Create feature DataFrame
            feature_df = pd.DataFrame(vol_features).dropna()
            
            if len(feature_df) < 50:
                raise ValueError("Insufficient data for volatility forecasting")
            
            # Prepare training data
            target = feature_df['rv_20'].shift(-1).dropna()  # Next day's volatility
            features = feature_df[:-1]  # All features except last
            
            # Split data
            split_idx = int(len(features) * 0.8)
            X_train, X_test = features[:split_idx], features[split_idx:]
            y_train, y_test = target[:split_idx], target[split_idx:]
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model (Random Forest for non-linear relationships)
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            train_score = model.score(X_train_scaled, y_train)
            test_score = model.score(X_test_scaled, y_test)
            
            # Generate forecast
            last_features = features.iloc[-1:].values
            last_features_scaled = self.scaler.transform(last_features)
            
            forecast = []
            current_features = last_features_scaled.copy()
            
            for _ in range(forecast_horizon):
                vol_pred = model.predict(current_features)[0]
                forecast.append(vol_pred)
                
                # Update features for next prediction (simplified approach)
                # In practice, you might use more sophisticated state updating
                current_features = current_features.copy()
            
            # Calculate forecast statistics
            forecast_mean = np.mean(forecast)
            forecast_std = np.std(forecast)
            current_vol = feature_df['rv_20'].iloc[-1]
            
            self.vol_forecast_model = model
            
            return {
                'success': True,
                'forecast': forecast,
                'forecast_horizon': forecast_horizon,
                'forecast_mean': forecast_mean,
                'forecast_std': forecast_std,
                'current_volatility': current_vol,
                'model_performance': {
                    'train_r2': train_score,
                    'test_r2': test_score,
                },
                'feature_importance': dict(zip(
                    X_train.columns,
                    model.feature_importances_
                )),
                'created_at': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error forecasting volatility: {e}")
            return {
                'success': False,
                'error': str(e),
                'forecast_horizon': forecast_horizon,
            }
    
    def calculate_term_structure(self) -> Dict[str, Any]:
        """
        Calculate implied volatility term structure.
        
        Returns:
            Dict containing term structure data
        """
        try:
            if self.iv_surface is None:
                raise ValueError("No volatility surface available")
            
            # Extract ATM volatilities across time
            tte_grid = self.iv_surface['tte_grid']
            iv_surface = self.iv_surface['iv_surface']
            
            # Find ATM index (moneyness = 1.0)
            moneyness_grid = self.iv_surface['moneyness_grid']
            atm_idx = np.argmin(np.abs(moneyness_grid - 1.0))
            
            # Extract term structure
            atm_ivs = iv_surface[:, atm_idx]
            
            # Calculate term structure slope
            valid_mask = ~np.isnan(atm_ivs)
            if np.sum(valid_mask) < 2:
                raise ValueError("Insufficient valid ATM volatilities")
            
            slope = np.polyfit(tte_grid[valid_mask], atm_ivs[valid_mask], 1)[0]
            
            return {
                'success': True,
                'time_to_expiry': tte_grid[valid_mask].tolist(),
                'atm_volatilities': atm_ivs[valid_mask].tolist(),
                'term_structure_slope': slope,
                'contango': slope > 0,  # Positive slope indicates contango
                'backwardation': slope < 0,  # Negative slope indicates backwardation
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating term structure: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def _calculate_surface_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate statistics for the volatility surface."""
        return {
            'mean_iv': df['implied_volatility'].mean(),
            'median_iv': df['implied_volatility'].median(),
            'std_iv': df['implied_volatility'].std(),
            'min_iv': df['implied_volatility'].min(),
            'max_iv': df['implied_volatility'].max(),
            'data_points': len(df),
        }
    
    def _get_nearest_valid_iv(self, moneyness: float, time_to_expiry: float) -> float:
        """Get nearest valid IV from surface."""
        try:
            if self.iv_surface is None:
                return 0.20
            
            # Use raw data to find nearest point
            df = self.iv_surface['raw_data']
            
            # Calculate distance to all points
            distances = np.sqrt(
                (df['moneyness'] - moneyness)**2 +
                (df['tte'] - time_to_expiry)**2
            )
            
            # Return IV of nearest point
            nearest_idx = distances.idxmin()
            return df.loc[nearest_idx, 'implied_volatility']
            
        except Exception:
            return 0.20  # Default volatility