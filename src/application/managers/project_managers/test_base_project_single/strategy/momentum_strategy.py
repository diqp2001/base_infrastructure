"""
Simple 200-day moving average momentum strategy.

Implements basic trend-following using 200-day moving averages
for clean, interpretable trading signals.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from ..config import DEFAULT_CONFIG


class SimpleMomentumStrategy:
    """
    Simple momentum strategy based on 200-day moving averages.
    Provides clear trend-following signals without complex ML components.
    """
    
    def __init__(self, 
                 moving_average_window: int = 200,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize simple momentum strategy.
        
        Args:
            moving_average_window: Window for moving average calculation (default 200)
            config: Strategy configuration (uses default if None)
        """
        self.moving_average_window = moving_average_window
        self.config = config or DEFAULT_CONFIG
        
        # Strategy parameters
        self.lookback_window = moving_average_window + 50  # Buffer for MA calculation
        self.rebalance_frequency = 'daily'  # Daily rebalancing for simple strategy
        self.max_position_size = 0.25  # Max 25% per position
        self.min_position_size = 0.01  # Min 1% per position
        
        # Simple binary signals - no complex thresholds needed
        self.signal_threshold = 0.0  # Simple above/below MA
        
        # Storage for calculated moving averages and signals
        self.moving_averages = {}
        self.current_signals = {}
        self.last_prices = {}
        self.max_drawdown = self.portfolio_config['RISK_MANAGEMENT']['max_drawdown']
        self.position_concentration = self.portfolio_config['RISK_MANAGEMENT']['position_concentration']
        
        # Internal state
        self.current_positions = {}
        self.signal_history = []
        self.performance_metrics = {}
    
    def get_signal_history(self) -> List[Dict]:
        """Get historical signals for analysis."""
        return self.signal_history
    
    def get_current_signals(self) -> Dict[str, float]:
        """Get current signal values."""
        return self.current_signals.copy()
    
    def get_moving_averages(self) -> Dict[str, float]:
        """Get current moving averages."""
        return self.moving_averages.copy()
    
    def get_last_prices(self) -> Dict[str, float]:
        """Get last observed prices."""
        return self.last_prices.copy()
    
    def generate_strategy_signals(self, 
                                market_data: pd.DataFrame,
                                factor_data: pd.DataFrame,
                                current_date: datetime) -> Dict[str, float]:
        """
        Generate simple trading signals based on 200-day moving averages.
        
        Args:
            market_data: Current market price data
            factor_data: Factor data with price information
            current_date: Current trading date
            
        Returns:
            Dictionary of signals by ticker (1.0 for long, -1.0 for short)
        """
        print(f"📊 Generating 200-day MA signals for {current_date.strftime('%Y-%m-%d')}")
        
        signals = {}
        
        # Use factor_data if available, otherwise market_data
        data_source = factor_data if not factor_data.empty else market_data
        
        if data_source.empty:
            print("  ⚠️  No data available for signal generation")
            return signals
        
        # Extract tickers and calculate signals
        tickers = self._extract_tickers_from_data(data_source)
        
        for ticker in tickers:
            try:
                signal = self._calculate_200_day_signal(data_source, ticker)
                if signal is not None:
                    signals[ticker] = signal
                    self.current_signals[ticker] = signal
                    
                    signal_text = "LONG" if signal > 0 else "SHORT"
                    print(f"  {ticker}: {signal_text} (signal: {signal})")
            except Exception as e:
                print(f"  ❌ Error calculating signal for {ticker}: {str(e)}")
        
        # Store signal history for analysis
        self.signal_history.append({
            'date': current_date,
            'signals': signals.copy()
        })
        
        print(f"  ✅ Generated signals for {len(signals)} assets")
        return signals
    
    def _extract_tickers_from_data(self, data: pd.DataFrame) -> List[str]:
        """Extract ticker symbols from DataFrame columns."""
        tickers = set()
        
        for col in data.columns:
            # Handle different column naming conventions
            if '_close_price' in col:
                ticker = col.replace('_close_price', '')
                tickers.add(ticker)
            elif 'close' in col.lower() and col.lower() != 'close':
                # Handle ticker_close format
                ticker = col.replace('_close', '').replace('_Close', '')
                tickers.add(ticker)
        
        # If no ticker-specific columns, assume single ticker data
        if not tickers and 'close' in data.columns:
            tickers.add('DEFAULT')
        
        return list(tickers)
    
    def _calculate_200_day_signal(self, data: pd.DataFrame, ticker: str) -> Optional[float]:
        """Calculate 200-day moving average signal for a ticker."""
        try:
            # Find price column for this ticker
            price_col = None
            possible_cols = [
                f'{ticker}_close_price',
                f'{ticker}_close',
                f'{ticker}_Close',
                'close',  # For single ticker data
                'Close'
            ]
            
            for col in possible_cols:
                if col in data.columns:
                    price_col = col
                    break
            
            if price_col is None:
                print(f"    No price column found for {ticker}")
                return None
            
            prices = data[price_col].dropna()
            
            if len(prices) < self.moving_average_window:
                print(f"    Insufficient data for {ticker}: {len(prices)} < {self.moving_average_window}")
                return None
            
            # Calculate 200-day moving average
            moving_avg = prices.rolling(window=self.moving_average_window).mean().iloc[-1]
            current_price = prices.iloc[-1]
            
            # Store for reference
            self.moving_averages[ticker] = moving_avg
            self.last_prices[ticker] = current_price
            
            # Generate binary signal
            signal = 1.0 if current_price > moving_avg else -1.0
            
            print(f"    {ticker}: Price ${current_price:.2f}, MA ${moving_avg:.2f}, Signal: {signal}")
            return signal
            
        except Exception as e:
            print(f"    Error calculating 200-day signal for {ticker}: {str(e)}")
            return None
                
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