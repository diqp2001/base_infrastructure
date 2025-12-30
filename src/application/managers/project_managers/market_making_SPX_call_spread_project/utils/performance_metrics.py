"""
Performance Metrics Calculator for SPX Call Spread Market Making

This module provides comprehensive performance analysis and metrics calculation
for the market making strategy.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class PerformanceCalculator:
    """
    Performance calculator for SPX call spread market making strategy.
    Provides comprehensive analysis of trading performance, risk metrics, and attribution.
    """
    
    def __init__(self):
        """Initialize the performance calculator."""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def calculate_strategy_performance(
        self,
        portfolio_history: List[Dict[str, Any]],
        benchmark_returns: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive strategy performance metrics.
        
        Args:
            portfolio_history: List of daily portfolio snapshots
            benchmark_returns: Optional benchmark returns for comparison
            
        Returns:
            Dict containing performance metrics
        """
        try:
            if not portfolio_history:
                raise ValueError("No portfolio history provided")
            
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame(portfolio_history)
            
            # Calculate returns
            returns = self._calculate_returns(df)
            
            # Basic performance metrics
            basic_metrics = self._calculate_basic_metrics(returns, df)
            
            # Risk metrics
            risk_metrics = self._calculate_risk_metrics(returns)
            
            # Drawdown analysis
            drawdown_metrics = self._calculate_drawdown_metrics(df)
            
            # Trade-based metrics
            trade_metrics = self._calculate_trade_metrics(portfolio_history)
            
            # Benchmark comparison (if provided)
            benchmark_metrics = {}
            if benchmark_returns:
                benchmark_metrics = self._calculate_benchmark_comparison(returns, benchmark_returns)
            
            # Rolling performance
            rolling_metrics = self._calculate_rolling_metrics(returns)
            
            return {
                'basic_performance': basic_metrics,
                'risk_metrics': risk_metrics,
                'drawdown_analysis': drawdown_metrics,
                'trade_analysis': trade_metrics,
                'benchmark_comparison': benchmark_metrics,
                'rolling_metrics': rolling_metrics,
                'calculation_timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating strategy performance: {e}")
            return {
                'error': str(e),
                'calculation_timestamp': datetime.now().isoformat(),
            }
    
    def calculate_position_performance(
        self,
        positions_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate performance metrics at the position level.
        
        Args:
            positions_history: List of position snapshots over time
            
        Returns:
            Dict containing position-level performance analysis
        """
        try:
            if not positions_history:
                return {'error': 'No position history provided'}
            
            # Analyze by position type
            position_types = {}
            total_pnl = 0
            winning_positions = 0
            losing_positions = 0
            
            for position_snapshot in positions_history:
                for position_id, position in position_snapshot.items():
                    position_type = position.get('type', 'unknown')
                    pnl = position.get('current_pnl', 0)
                    
                    if position_type not in position_types:
                        position_types[position_type] = {
                            'count': 0,
                            'total_pnl': 0,
                            'wins': 0,
                            'losses': 0,
                        }
                    
                    position_types[position_type]['count'] += 1
                    position_types[position_type]['total_pnl'] += pnl
                    total_pnl += pnl
                    
                    if pnl > 0:
                        position_types[position_type]['wins'] += 1
                        winning_positions += 1
                    elif pnl < 0:
                        position_types[position_type]['losses'] += 1
                        losing_positions += 1
            
            # Calculate win rates by position type
            for pos_type, metrics in position_types.items():
                total_positions = metrics['wins'] + metrics['losses']
                metrics['win_rate'] = metrics['wins'] / total_positions if total_positions > 0 else 0
                metrics['avg_pnl'] = metrics['total_pnl'] / metrics['count'] if metrics['count'] > 0 else 0
            
            overall_win_rate = winning_positions / (winning_positions + losing_positions) if (winning_positions + losing_positions) > 0 else 0
            
            return {
                'position_type_analysis': position_types,
                'overall_metrics': {
                    'total_pnl': total_pnl,
                    'winning_positions': winning_positions,
                    'losing_positions': losing_positions,
                    'overall_win_rate': overall_win_rate,
                },
                'analysis_timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating position performance: {e}")
            return {
                'error': str(e),
                'analysis_timestamp': datetime.now().isoformat(),
            }
    
    def calculate_risk_adjusted_returns(
        self,
        returns: List[float],
        risk_free_rate: float = 0.02
    ) -> Dict[str, Any]:
        """
        Calculate risk-adjusted return metrics.
        
        Args:
            returns: List of periodic returns
            risk_free_rate: Risk-free rate for calculations
            
        Returns:
            Dict containing risk-adjusted metrics
        """
        try:
            if not returns:
                raise ValueError("No returns provided")
            
            returns_array = np.array(returns)
            
            # Basic statistics
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            
            # Annualized metrics (assuming daily returns)
            annualized_return = (1 + mean_return) ** 252 - 1
            annualized_volatility = std_return * np.sqrt(252)
            
            # Sharpe ratio
            excess_return = annualized_return - risk_free_rate
            sharpe_ratio = excess_return / annualized_volatility if annualized_volatility != 0 else 0
            
            # Sortino ratio (downside deviation)
            downside_returns = returns_array[returns_array < 0]
            downside_deviation = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 0 else 0
            sortino_ratio = excess_return / downside_deviation if downside_deviation != 0 else 0
            
            # Calmar ratio (return vs max drawdown)
            cumulative_returns = np.cumprod(1 + returns_array)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (cumulative_returns - running_max) / running_max
            max_drawdown = abs(np.min(drawdowns))
            calmar_ratio = annualized_return / max_drawdown if max_drawdown != 0 else 0
            
            # Information ratio components
            tracking_error = std_return * np.sqrt(252)  # Annualized
            information_ratio = excess_return / tracking_error if tracking_error != 0 else 0
            
            # Skewness and kurtosis
            skewness = self._calculate_skewness(returns_array)
            kurtosis = self._calculate_kurtosis(returns_array)
            
            return {
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'calmar_ratio': calmar_ratio,
                'information_ratio': information_ratio,
                'annualized_return': annualized_return,
                'annualized_volatility': annualized_volatility,
                'max_drawdown': max_drawdown,
                'downside_deviation': downside_deviation,
                'skewness': skewness,
                'kurtosis': kurtosis,
                'excess_return': excess_return,
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating risk-adjusted returns: {e}")
            return {
                'error': str(e),
            }
    
    def _calculate_returns(self, df: pd.DataFrame) -> np.ndarray:
        """Calculate returns from portfolio values."""
        if 'portfolio_value' in df.columns:
            portfolio_values = df['portfolio_value'].values
            returns = np.diff(portfolio_values) / portfolio_values[:-1]
            return returns
        else:
            # Calculate from daily P&L
            daily_pnl = df['daily_pnl'].values if 'daily_pnl' in df.columns else np.zeros(len(df))
            portfolio_values = df.get('portfolio_value', np.ones(len(df)) * 100000).values
            returns = daily_pnl / portfolio_values
            return returns
    
    def _calculate_basic_metrics(self, returns: np.ndarray, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate basic performance metrics."""
        initial_value = df['portfolio_value'].iloc[0] if 'portfolio_value' in df.columns else 100000
        final_value = df['portfolio_value'].iloc[-1] if 'portfolio_value' in df.columns else 100000
        
        total_return = (final_value - initial_value) / initial_value
        trading_days = len(returns)
        
        # Annualized return
        if trading_days > 0:
            annualized_return = (1 + total_return) ** (252 / trading_days) - 1
        else:
            annualized_return = 0
        
        # Win rate
        positive_days = np.sum(returns > 0)
        win_rate = positive_days / len(returns) if len(returns) > 0 else 0
        
        # Average return
        avg_daily_return = np.mean(returns) if len(returns) > 0 else 0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'trading_days': trading_days,
            'win_rate': win_rate,
            'average_daily_return': avg_daily_return,
            'initial_value': initial_value,
            'final_value': final_value,
        }
    
    def _calculate_risk_metrics(self, returns: np.ndarray) -> Dict[str, Any]:
        """Calculate risk metrics."""
        if len(returns) == 0:
            return {'error': 'No returns data'}
        
        # Volatility
        daily_volatility = np.std(returns)
        annualized_volatility = daily_volatility * np.sqrt(252)
        
        # VaR (Value at Risk)
        var_95 = np.percentile(returns, 5)  # 5th percentile
        var_99 = np.percentile(returns, 1)  # 1st percentile
        
        # Expected Shortfall (Conditional VaR)
        es_95 = np.mean(returns[returns <= var_95]) if np.any(returns <= var_95) else var_95
        es_99 = np.mean(returns[returns <= var_99]) if np.any(returns <= var_99) else var_99
        
        # Maximum single-day loss
        max_daily_loss = np.min(returns)
        max_daily_gain = np.max(returns)
        
        return {
            'daily_volatility': daily_volatility,
            'annualized_volatility': annualized_volatility,
            'var_95': var_95,
            'var_99': var_99,
            'expected_shortfall_95': es_95,
            'expected_shortfall_99': es_99,
            'max_daily_loss': max_daily_loss,
            'max_daily_gain': max_daily_gain,
        }
    
    def _calculate_drawdown_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate drawdown analysis."""
        if 'portfolio_value' not in df.columns:
            return {'error': 'No portfolio value data'}
        
        portfolio_values = df['portfolio_value'].values
        
        # Calculate running maximum
        running_max = np.maximum.accumulate(portfolio_values)
        
        # Calculate drawdowns
        drawdowns = (portfolio_values - running_max) / running_max
        
        # Maximum drawdown
        max_drawdown = np.min(drawdowns)
        
        # Drawdown duration analysis
        in_drawdown = drawdowns < -0.001  # More than 0.1% down
        drawdown_periods = self._identify_drawdown_periods(in_drawdown)
        
        max_drawdown_duration = 0
        if drawdown_periods:
            max_drawdown_duration = max(period['duration'] for period in drawdown_periods)
        
        # Average drawdown
        drawdown_values = drawdowns[drawdowns < 0]
        avg_drawdown = np.mean(drawdown_values) if len(drawdown_values) > 0 else 0
        
        return {
            'max_drawdown': max_drawdown,
            'max_drawdown_duration': max_drawdown_duration,
            'average_drawdown': avg_drawdown,
            'drawdown_periods_count': len(drawdown_periods),
            'current_drawdown': drawdowns[-1],
        }
    
    def _calculate_trade_metrics(self, portfolio_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trade-based performance metrics."""
        total_trades = 0
        position_counts = []
        
        for snapshot in portfolio_history:
            if 'position_count' in snapshot:
                position_counts.append(snapshot['position_count'])
            if 'total_trades' in snapshot:
                total_trades = max(total_trades, snapshot['total_trades'])
        
        avg_positions = np.mean(position_counts) if position_counts else 0
        max_positions = max(position_counts) if position_counts else 0
        
        return {
            'total_trades_executed': total_trades,
            'average_positions': avg_positions,
            'maximum_positions': max_positions,
            'portfolio_utilization': avg_positions / max_positions if max_positions > 0 else 0,
        }
    
    def _calculate_benchmark_comparison(
        self,
        strategy_returns: np.ndarray,
        benchmark_returns: List[float]
    ) -> Dict[str, Any]:
        """Calculate benchmark comparison metrics."""
        try:
            benchmark_array = np.array(benchmark_returns[:len(strategy_returns)])
            
            # Tracking error
            excess_returns = strategy_returns - benchmark_array
            tracking_error = np.std(excess_returns) * np.sqrt(252)
            
            # Information ratio
            avg_excess_return = np.mean(excess_returns) * 252  # Annualized
            information_ratio = avg_excess_return / tracking_error if tracking_error != 0 else 0
            
            # Beta calculation
            covariance = np.cov(strategy_returns, benchmark_array)[0, 1]
            benchmark_variance = np.var(benchmark_array)
            beta = covariance / benchmark_variance if benchmark_variance != 0 else 0
            
            # Alpha calculation
            benchmark_return = np.mean(benchmark_array) * 252
            strategy_return = np.mean(strategy_returns) * 252
            alpha = strategy_return - beta * benchmark_return
            
            return {
                'tracking_error': tracking_error,
                'information_ratio': information_ratio,
                'beta': beta,
                'alpha': alpha,
                'correlation': np.corrcoef(strategy_returns, benchmark_array)[0, 1],
                'avg_excess_return': avg_excess_return,
            }
            
        except Exception as e:
            self.logger.error(f"Error in benchmark comparison: {e}")
            return {'error': str(e)}
    
    def _calculate_rolling_metrics(self, returns: np.ndarray, window: int = 30) -> Dict[str, Any]:
        """Calculate rolling performance metrics."""
        try:
            if len(returns) < window:
                return {'error': f'Insufficient data for {window}-day rolling metrics'}
            
            rolling_returns = []
            rolling_volatility = []
            rolling_sharpe = []
            
            for i in range(window, len(returns)):
                period_returns = returns[i-window:i]
                
                # Rolling return
                period_return = np.mean(period_returns) * 252
                rolling_returns.append(period_return)
                
                # Rolling volatility
                period_vol = np.std(period_returns) * np.sqrt(252)
                rolling_volatility.append(period_vol)
                
                # Rolling Sharpe (assuming 2% risk-free rate)
                sharpe = (period_return - 0.02) / period_vol if period_vol != 0 else 0
                rolling_sharpe.append(sharpe)
            
            return {
                'rolling_return_mean': np.mean(rolling_returns),
                'rolling_return_std': np.std(rolling_returns),
                'rolling_volatility_mean': np.mean(rolling_volatility),
                'rolling_volatility_std': np.std(rolling_volatility),
                'rolling_sharpe_mean': np.mean(rolling_sharpe),
                'rolling_sharpe_std': np.std(rolling_sharpe),
                'best_rolling_period': np.max(rolling_returns),
                'worst_rolling_period': np.min(rolling_returns),
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating rolling metrics: {e}")
            return {'error': str(e)}
    
    def _identify_drawdown_periods(self, in_drawdown: np.ndarray) -> List[Dict[str, Any]]:
        """Identify distinct drawdown periods."""
        periods = []
        start_idx = None
        
        for i, is_down in enumerate(in_drawdown):
            if is_down and start_idx is None:
                start_idx = i
            elif not is_down and start_idx is not None:
                periods.append({
                    'start': start_idx,
                    'end': i - 1,
                    'duration': i - start_idx,
                })
                start_idx = None
        
        # Handle case where drawdown continues to end
        if start_idx is not None:
            periods.append({
                'start': start_idx,
                'end': len(in_drawdown) - 1,
                'duration': len(in_drawdown) - start_idx,
            })
        
        return periods
    
    def _calculate_skewness(self, returns: np.ndarray) -> float:
        """Calculate skewness of returns."""
        if len(returns) < 3:
            return 0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0
        
        skewness = np.mean(((returns - mean_return) / std_return) ** 3)
        return skewness
    
    def _calculate_kurtosis(self, returns: np.ndarray) -> float:
        """Calculate kurtosis of returns."""
        if len(returns) < 4:
            return 0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0
        
        kurtosis = np.mean(((returns - mean_return) / std_return) ** 4) - 3
        return kurtosis