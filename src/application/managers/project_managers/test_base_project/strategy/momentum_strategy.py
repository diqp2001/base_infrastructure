"""
Spatiotemporal momentum strategy combining ML signals with traditional momentum.

Integrates trained TFT/MLP models with momentum-based trading 
and factor-driven signal generation.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from ..models.spatiotemporal_model import HybridSpatiotemporalModel
from ..config import DEFAULT_CONFIG


class SpatiotemporalMomentumStrategy:
    """
    Advanced momentum strategy that combines spatiotemporal model predictions
    with traditional momentum signals and factor-based risk management.
    """
    
    def __init__(self, 
                 trained_model: HybridSpatiotemporalModel,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize spatiotemporal momentum strategy.
        
        Args:
            trained_model: Pre-trained hybrid spatiotemporal model
            config: Strategy configuration (uses default if None)
        """
        self.trained_model = trained_model
        self.config = config or DEFAULT_CONFIG
        self.backtest_config = self.config['BACKTEST']
        self.portfolio_config = self.config['PORTFOLIO']
        
        # Strategy parameters
        self.lookback_window = 252  # 1 year lookback
        self.rebalance_frequency = self.backtest_config['REBALANCE_FREQUENCY']
        self.max_position_size = self.backtest_config['MAX_POSITION_SIZE']
        self.min_position_size = self.backtest_config['MIN_POSITION_SIZE']
        
        # Signal thresholds
        self.ml_signal_threshold = 0.6
        self.momentum_signal_threshold = 0.5
        self.combined_signal_threshold = 0.7
        
        # Risk management parameters
        self.max_volatility = self.portfolio_config['RISK_MANAGEMENT']['max_volatility']
        self.max_drawdown = self.portfolio_config['RISK_MANAGEMENT']['max_drawdown']
        self.position_concentration = self.portfolio_config['RISK_MANAGEMENT']['position_concentration']
        
        # Internal state
        self.current_positions = {}
        self.signal_history = []
        self.performance_metrics = {}
    
    def generate_strategy_signals(self, 
                                market_data: pd.DataFrame,
                                factor_data: pd.DataFrame,
                                current_date: datetime) -> Dict[str, float]:
        """
        Generate trading signals combining ML predictions with momentum analysis.
        
        Args:
            market_data: Current market price data
            factor_data: Factor data for signal generation
            current_date: Current trading date
            
        Returns:
            Dictionary of signals by ticker (-1 to 1, where 1 is max long)
        """
        print(f"📊 Generating strategy signals for {current_date.strftime('%Y-%m-%d')}")
        
        # Step 1: Get ML model signals
        ml_signals = self.trained_model.generate_signals_from_factors(
            factor_data, 
            model_type='ensemble',
            confidence_threshold=self.ml_signal_threshold
        )
        
        # Step 2: Calculate traditional momentum signals
        momentum_signals = self._calculate_momentum_signals(market_data, current_date)
        
        # Step 3: Combine ML and momentum signals
        combined_signals = self._combine_signals(ml_signals, momentum_signals)
        
        # Step 4: Apply risk management filters
        final_signals = self._apply_risk_filters(combined_signals, market_data, current_date)
        
        # Step 5: Normalize signal strengths
        normalized_signals = self._normalize_signal_strengths(final_signals)
        
        # Store signal history for analysis
        self.signal_history.append({
            'date': current_date,
            'ml_signals': ml_signals.to_dict() if hasattr(ml_signals, 'to_dict') else ml_signals,
            'momentum_signals': momentum_signals,
            'combined_signals': combined_signals,
            'final_signals': normalized_signals
        })
        
        print(f"  ✅ Generated signals for {len(normalized_signals)} assets")
        return normalized_signals
    
    def _calculate_momentum_signals(self, 
                                  market_data: pd.DataFrame, 
                                  current_date: datetime) -> Dict[str, float]:
        """Calculate traditional momentum signals."""
        momentum_signals = {}
        
        # Get data up to current date
        historical_data = market_data[market_data.index <= current_date].copy()
        
        if len(historical_data) < self.lookback_window:
            print(f"  ⚠️  Insufficient historical data: {len(historical_data)} < {self.lookback_window}")
            return {}
        
        # Extract tickers from column names
        tickers = set()
        for col in historical_data.columns:
            if '_close_price' in col:
                ticker = col.replace('_close_price', '')
                tickers.add(ticker)
        
        for ticker in tickers:
            try:
                price_col = f'{ticker}_close_price'
                if price_col not in historical_data.columns:
                    continue
                
                prices = historical_data[price_col].dropna()
                if len(prices) < self.lookback_window:
                    continue
                
                # Calculate multiple momentum signals
                signals = {}
                
                # 1. Price momentum (various periods)
                for period in [21, 63, 126, 252]:  # 1m, 3m, 6m, 1y
                    if len(prices) >= period:
                        momentum = (prices.iloc[-1] / prices.iloc[-period]) - 1
                        signals[f'momentum_{period}d'] = momentum
                
                # 2. Moving average signals
                for ma_period in [20, 50, 200]:
                    if len(prices) >= ma_period:
                        ma = prices.rolling(window=ma_period).mean().iloc[-1]
                        ma_signal = (prices.iloc[-1] / ma) - 1
                        signals[f'ma_signal_{ma_period}d'] = ma_signal
                
                # 3. Trend strength (linear regression slope)
                if len(prices) >= 63:
                    recent_prices = prices.tail(63)
                    x = np.arange(len(recent_prices))
                    slope, _ = np.polyfit(x, recent_prices.values, 1)
                    normalized_slope = slope / recent_prices.mean()
                    signals['trend_strength'] = normalized_slope
                
                # 4. Volatility-adjusted momentum
                if len(prices) >= 126:
                    returns = prices.pct_change().dropna()
                    if len(returns) >= 63:
                        momentum_126 = (prices.iloc[-1] / prices.iloc[-126]) - 1
                        volatility = returns.tail(63).std() * np.sqrt(252)
                        vol_adj_momentum = momentum_126 / max(volatility, 0.01)
                        signals['vol_adj_momentum'] = vol_adj_momentum
                
                # Combine momentum signals with weights
                signal_weights = {
                    'momentum_63d': 0.3,
                    'momentum_126d': 0.25,
                    'ma_signal_50d': 0.2,
                    'trend_strength': 0.15,
                    'vol_adj_momentum': 0.1
                }
                
                combined_momentum = 0.0
                total_weight = 0.0
                
                for signal_name, weight in signal_weights.items():
                    if signal_name in signals:
                        combined_momentum += signals[signal_name] * weight
                        total_weight += weight
                
                if total_weight > 0:
                    momentum_signals[ticker] = combined_momentum / total_weight
                
            except Exception as e:
                print(f"  ⚠️  Error calculating momentum for {ticker}: {str(e)}")
                continue
        
        return momentum_signals
    
    def _combine_signals(self, 
                        ml_signals: pd.DataFrame, 
                        momentum_signals: Dict[str, float]) -> Dict[str, float]:
        """Combine ML model signals with traditional momentum signals."""
        combined_signals = {}
        
        # Extract tickers from ML signals
        if hasattr(ml_signals, 'index'):
            ml_signal_dict = {}
            for idx in ml_signals.index:
                # Assuming signals are generated per ticker or have ticker info
                # This is a simplified extraction - adapt based on actual ML signal format
                ticker = str(idx).split('_')[0] if '_' in str(idx) else str(idx)
                if 'signal_strength' in ml_signals.columns:
                    ml_signal_dict[ticker] = ml_signals.loc[idx, 'signal_strength']
        else:
            ml_signal_dict = ml_signals if isinstance(ml_signals, dict) else {}
        
        # Combine signals for each ticker
        all_tickers = set(ml_signal_dict.keys()) | set(momentum_signals.keys())
        
        for ticker in all_tickers:
            ml_signal = ml_signal_dict.get(ticker, 0.0)
            momentum_signal = momentum_signals.get(ticker, 0.0)
            
            # Weighted combination (ML gets higher weight)
            ml_weight = 0.7
            momentum_weight = 0.3
            
            combined_signal = (ml_signal * ml_weight) + (momentum_signal * momentum_weight)
            
            # Apply combined signal threshold
            if abs(combined_signal) >= self.combined_signal_threshold:
                combined_signals[ticker] = combined_signal
        
        return combined_signals
    
    def _apply_risk_filters(self, 
                          signals: Dict[str, float],
                          market_data: pd.DataFrame,
                          current_date: datetime) -> Dict[str, float]:
        """Apply risk management filters to signals."""
        filtered_signals = {}
        
        # Get recent market data for risk calculations
        recent_data = market_data[market_data.index <= current_date].tail(252)
        
        for ticker, signal in signals.items():
            try:
                price_col = f'{ticker}_close_price'
                if price_col not in recent_data.columns:
                    continue
                
                prices = recent_data[price_col].dropna()
                if len(prices) < 63:
                    continue
                
                # Calculate risk metrics
                returns = prices.pct_change().dropna()
                
                # 1. Volatility filter
                volatility = returns.std() * np.sqrt(252)
                if volatility > self.max_volatility * 1.5:  # Extra buffer
                    signal *= 0.5  # Reduce signal strength
                
                # 2. Maximum drawdown filter
                rolling_max = prices.rolling(window=252, min_periods=63).max()
                current_drawdown = (prices.iloc[-1] / rolling_max.iloc[-1]) - 1
                if current_drawdown < -self.max_drawdown:
                    signal *= 0.3  # Significantly reduce signal
                
                # 3. Liquidity filter (using volume if available)
                volume_col = f'{ticker}_volume'
                if volume_col in recent_data.columns:
                    avg_volume = recent_data[volume_col].tail(21).mean()
                    if avg_volume < 1000000:  # Low liquidity threshold
                        signal *= 0.7
                
                # 4. Position concentration filter
                if abs(signal) > self.position_concentration:
                    signal = np.sign(signal) * self.position_concentration
                
                # 5. Minimum position size filter
                if abs(signal) > 0 and abs(signal) < self.min_position_size:
                    signal = 0.0  # Remove very small positions
                
                filtered_signals[ticker] = signal
                
            except Exception as e:
                print(f"  ⚠️  Error applying risk filter for {ticker}: {str(e)}")
                continue
        
        return filtered_signals
    
    def _normalize_signal_strengths(self, signals: Dict[str, float]) -> Dict[str, float]:
        """Normalize signal strengths to ensure they sum to reasonable levels."""
        if not signals:
            return {}
        
        # Calculate absolute signal sum
        total_abs_signal = sum(abs(signal) for signal in signals.values())
        
        if total_abs_signal == 0:
            return {}
        
        # Target total exposure (configurable)
        target_exposure = 1.0  # 100% of portfolio
        
        # Scale signals if they exceed target exposure
        if total_abs_signal > target_exposure:
            scale_factor = target_exposure / total_abs_signal
            normalized_signals = {ticker: signal * scale_factor 
                                for ticker, signal in signals.items()}
        else:
            normalized_signals = signals.copy()
        
        # Apply position size limits
        final_signals = {}
        for ticker, signal in normalized_signals.items():
            # Ensure signal is within position limits
            if signal > self.max_position_size:
                signal = self.max_position_size
            elif signal < -self.max_position_size:
                signal = -self.max_position_size
            
            final_signals[ticker] = signal
        
        return final_signals
    
    def update_positions(self, new_signals: Dict[str, float], current_date: datetime):
        """Update current positions based on new signals."""
        self.current_positions = new_signals.copy()
        
        print(f"📈 Updated positions for {current_date.strftime('%Y-%m-%d')}:")
        for ticker, position in self.current_positions.items():
            if abs(position) > 0.01:  # Only show significant positions
                direction = "LONG" if position > 0 else "SHORT"
                print(f"  {ticker}: {direction} {abs(position):.3f}")
    
    def get_current_positions(self) -> Dict[str, float]:
        """Get current position sizes."""
        return self.current_positions.copy()
    
    def calculate_strategy_performance(self, 
                                     market_data: pd.DataFrame,
                                     start_date: datetime,
                                     end_date: datetime) -> Dict[str, Any]:
        """Calculate strategy performance metrics."""
        # This is a placeholder for performance calculation
        # In a real implementation, you would calculate returns, Sharpe ratio, etc.
        
        performance = {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'number_of_trades': len(self.signal_history),
            'avg_position_size': np.mean([abs(pos) for positions in 
                                        [s['final_signals'] for s in self.signal_history]
                                        for pos in positions.values()]) if self.signal_history else 0.0
        }
        
        return performance
    
    def get_signal_history(self) -> List[Dict[str, Any]]:
        """Get historical signals for analysis."""
        return self.signal_history.copy()
    
    def reset_strategy_state(self):
        """Reset strategy state for new backtest."""
        self.current_positions = {}
        self.signal_history = []
        self.performance_metrics = {}
        print("🔄 Strategy state reset")