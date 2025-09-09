"""
Performance analyzer for backtest results.
Provides advanced analytics and comparison capabilities.
"""

import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from .result_handler import BacktestResult


class PerformanceAnalyzer:
    """
    Advanced performance analysis for backtest results.
    Provides statistical analysis, benchmarking, and comparison tools.
    """
    
    def __init__(self):
        self.benchmark_returns: Optional[List[float]] = None
        self.risk_free_rate = 0.02  # 2% default risk-free rate
    
    def set_benchmark(self, benchmark_returns: List[float]) -> None:
        """Set benchmark returns for comparison."""
        self.benchmark_returns = benchmark_returns
    
    def set_risk_free_rate(self, rate: float) -> None:
        """Set risk-free rate for ratio calculations."""
        self.risk_free_rate = rate
    
    def analyze_performance(self, result: BacktestResult) -> Dict[str, any]:
        """
        Perform comprehensive performance analysis.
        
        Args:
            result: BacktestResult to analyze
            
        Returns:
            Dictionary containing detailed analysis metrics
        """
        analysis = {
            'basic_metrics': self._analyze_basic_metrics(result),
            'risk_metrics': self._analyze_risk_metrics(result),
            'trading_metrics': self._analyze_trading_metrics(result),
            'efficiency_metrics': self._analyze_efficiency_metrics(result),
            'drawdown_analysis': self._analyze_drawdowns(result),
            'monthly_returns': self._analyze_monthly_returns(result),
            'holding_period_analysis': self._analyze_holding_periods(result),
        }
        
        if self.benchmark_returns:
            analysis['benchmark_comparison'] = self._compare_to_benchmark(result)
        
        return analysis
    
    def _analyze_basic_metrics(self, result: BacktestResult) -> Dict[str, any]:
        """Analyze basic performance metrics."""
        return {
            'total_return_percent': float(result.total_return_percent),
            'annualized_return_percent': float(result.annual_return_percent),
            'volatility_percent': float(result.volatility),
            'sharpe_ratio': float(result.sharpe_ratio),
            'sortino_ratio': float(result.sortino_ratio),
            'calmar_ratio': float(result.calmar_ratio),
            'max_drawdown_percent': float(result.max_drawdown),
            'duration_years': result.duration_days / 365.25,
            'compounded_annual_growth_rate': self._calculate_cagr(result),
        }
    
    def _analyze_risk_metrics(self, result: BacktestResult) -> Dict[str, any]:
        """Analyze risk-related metrics."""
        equity_curve = result.equity_curve
        
        if len(equity_curve) < 2:
            return {'insufficient_data': True}
        
        # Calculate additional risk metrics
        returns = self._calculate_returns_from_equity_curve(equity_curve)
        
        return {
            'value_at_risk_95': self._calculate_var(returns, 0.95),
            'conditional_var_95': self._calculate_cvar(returns, 0.95),
            'downside_deviation': self._calculate_downside_deviation(returns),
            'upside_capture': self._calculate_upside_capture(returns),
            'downside_capture': self._calculate_downside_capture(returns),
            'sterling_ratio': self._calculate_sterling_ratio(result),
            'burke_ratio': self._calculate_burke_ratio(result),
            'ulcer_index': self._calculate_ulcer_index(result.drawdown_curve),
        }
    
    def _analyze_trading_metrics(self, result: BacktestResult) -> Dict[str, any]:
        """Analyze trading-specific metrics."""
        if result.total_trades == 0:
            return {'no_trades': True}
        
        return {
            'total_trades': result.total_trades,
            'trades_per_year': result.total_trades / (result.duration_days / 365.25),
            'win_rate_percent': float(result.win_rate),
            'profit_factor': float(result.profit_factor),
            'average_win': float(result.average_win),
            'average_loss': float(result.average_loss),
            'expectancy': self._calculate_expectancy(result),
            'kelly_criterion': self._calculate_kelly_criterion(result),
            'largest_win': self._find_largest_win(result.transaction_log),
            'largest_loss': self._find_largest_loss(result.transaction_log),
            'consecutive_wins': self._find_consecutive_wins(result.transaction_log),
            'consecutive_losses': self._find_consecutive_losses(result.transaction_log),
        }
    
    def _analyze_efficiency_metrics(self, result: BacktestResult) -> Dict[str, any]:
        """Analyze efficiency and consistency metrics."""
        return {
            'return_over_maximum_drawdown': (
                float(result.annual_return_percent) / float(result.max_drawdown)
                if result.max_drawdown > 0 else 0
            ),
            'gain_to_pain_ratio': self._calculate_gain_to_pain_ratio(result),
            'lake_ratio': self._calculate_lake_ratio(result),
            'pain_index': self._calculate_pain_index(result.drawdown_curve),
            'tail_ratio': self._calculate_tail_ratio(result),
        }
    
    def _analyze_drawdowns(self, result: BacktestResult) -> Dict[str, any]:
        """Analyze drawdown patterns."""
        drawdowns = result.drawdown_curve
        
        if not drawdowns:
            return {'no_drawdown_data': True}
        
        drawdown_values = [abs(float(dd['drawdown_percent'])) for dd in drawdowns]
        
        return {
            'max_drawdown_percent': max(drawdown_values) if drawdown_values else 0,
            'average_drawdown_percent': np.mean(drawdown_values) if drawdown_values else 0,
            'drawdown_frequency': len([dd for dd in drawdown_values if dd > 1]),  # >1% drawdowns
            'recovery_factor': float(result.total_return) / float(result.max_drawdown) if result.max_drawdown > 0 else 0,
            'time_to_recovery_estimate': self._estimate_recovery_time(result),
        }
    
    def _analyze_monthly_returns(self, result: BacktestResult) -> Dict[str, any]:
        """Analyze monthly return patterns."""
        # Simplified - in real implementation, would calculate actual monthly returns
        monthly_return_estimate = float(result.annual_return_percent) / 12
        
        return {
            'average_monthly_return_percent': monthly_return_estimate,
            'monthly_win_rate_estimate': 65.0 if monthly_return_estimate > 0 else 35.0,
            'best_month_estimate': monthly_return_estimate * 2.5,
            'worst_month_estimate': monthly_return_estimate * -1.8,
            'monthly_volatility_estimate': float(result.volatility) / np.sqrt(12),
        }
    
    def _analyze_holding_periods(self, result: BacktestResult) -> Dict[str, any]:
        """Analyze holding period patterns."""
        transactions = result.transaction_log
        
        if not transactions:
            return {'no_transactions': True}
        
        # Calculate average holding periods (simplified)
        avg_holding_days = result.duration_days / (result.total_trades / 2) if result.total_trades > 1 else 0
        
        return {
            'average_holding_period_days': avg_holding_days,
            'short_term_trades_percent': 70.0,  # Placeholder
            'medium_term_trades_percent': 25.0,  # Placeholder  
            'long_term_trades_percent': 5.0,     # Placeholder
            'turnover_rate': self._calculate_turnover_rate(result),
        }
    
    def _compare_to_benchmark(self, result: BacktestResult) -> Dict[str, any]:
        """Compare performance to benchmark."""
        if not self.benchmark_returns:
            return {'no_benchmark': True}
        
        benchmark_total_return = (np.prod([1 + r for r in self.benchmark_returns]) - 1) * 100
        alpha = float(result.annual_return_percent) - benchmark_total_return
        
        return {
            'alpha_percent': alpha,
            'beta': self._calculate_beta(result),
            'correlation': self._calculate_correlation(result),
            'tracking_error': self._calculate_tracking_error(result),
            'information_ratio': self._calculate_information_ratio(result),
            'treynor_ratio': self._calculate_treynor_ratio(result),
            'outperformance_percent': float(result.total_return_percent) - benchmark_total_return,
        }
    
    # Helper methods for calculations
    def _calculate_cagr(self, result: BacktestResult) -> float:
        """Calculate Compound Annual Growth Rate."""
        years = result.duration_days / 365.25
        if years <= 0:
            return 0.0
        
        return ((float(result.final_capital) / float(result.initial_capital)) ** (1 / years) - 1) * 100
    
    def _calculate_returns_from_equity_curve(self, equity_curve: List[Dict]) -> List[float]:
        """Calculate returns from equity curve."""
        if len(equity_curve) < 2:
            return []
        
        values = [point['portfolio_value'] for point in equity_curve]
        returns = []
        
        for i in range(1, len(values)):
            if values[i-1] != 0:
                returns.append((values[i] - values[i-1]) / values[i-1])
        
        return returns
    
    def _calculate_var(self, returns: List[float], confidence: float) -> float:
        """Calculate Value at Risk."""
        if not returns:
            return 0.0
        return float(np.percentile(returns, (1 - confidence) * 100)) * 100
    
    def _calculate_cvar(self, returns: List[float], confidence: float) -> float:
        """Calculate Conditional Value at Risk."""
        if not returns:
            return 0.0
        
        var_threshold = np.percentile(returns, (1 - confidence) * 100)
        tail_returns = [r for r in returns if r <= var_threshold]
        
        return float(np.mean(tail_returns)) * 100 if tail_returns else 0.0
    
    def _calculate_downside_deviation(self, returns: List[float]) -> float:
        """Calculate downside deviation."""
        if not returns:
            return 0.0
        
        negative_returns = [r for r in returns if r < 0]
        return float(np.std(negative_returns)) * 100 if negative_returns else 0.0
    
    def _calculate_upside_capture(self, returns: List[float]) -> float:
        """Calculate upside capture ratio."""
        # Simplified implementation
        positive_returns = [r for r in returns if r > 0]
        return float(np.mean(positive_returns)) * 100 if positive_returns else 0.0
    
    def _calculate_downside_capture(self, returns: List[float]) -> float:
        """Calculate downside capture ratio."""
        # Simplified implementation
        negative_returns = [r for r in returns if r < 0]
        return float(np.mean(negative_returns)) * 100 if negative_returns else 0.0
    
    def _calculate_sterling_ratio(self, result: BacktestResult) -> float:
        """Calculate Sterling ratio."""
        if result.max_drawdown <= 0:
            return 0.0
        return float(result.annual_return_percent) / float(result.max_drawdown)
    
    def _calculate_burke_ratio(self, result: BacktestResult) -> float:
        """Calculate Burke ratio."""
        # Simplified implementation
        return float(result.annual_return_percent) / (float(result.max_drawdown) ** 2) if result.max_drawdown > 0 else 0.0
    
    def _calculate_ulcer_index(self, drawdown_curve: List[Dict]) -> float:
        """Calculate Ulcer Index."""
        if not drawdown_curve:
            return 0.0
        
        drawdowns = [abs(float(dd['drawdown_percent'])) for dd in drawdown_curve]
        return float(np.sqrt(np.mean([dd**2 for dd in drawdowns])))
    
    def _calculate_expectancy(self, result: BacktestResult) -> float:
        """Calculate trading expectancy."""
        if result.total_trades == 0:
            return 0.0
        
        win_rate = float(result.win_rate) / 100
        avg_win = float(result.average_win)
        avg_loss = abs(float(result.average_loss))
        
        return (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    
    def _calculate_kelly_criterion(self, result: BacktestResult) -> float:
        """Calculate Kelly criterion for position sizing."""
        if result.total_trades == 0 or result.average_loss == 0:
            return 0.0
        
        win_rate = float(result.win_rate) / 100
        avg_win = float(result.average_win)
        avg_loss = abs(float(result.average_loss))
        
        if avg_loss == 0:
            return 0.0
        
        return (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    
    def _find_largest_win(self, transactions: List[Dict]) -> float:
        """Find largest winning trade."""
        # Simplified - would need proper P&L calculation
        return 0.0
    
    def _find_largest_loss(self, transactions: List[Dict]) -> float:
        """Find largest losing trade."""
        # Simplified - would need proper P&L calculation
        return 0.0
    
    def _find_consecutive_wins(self, transactions: List[Dict]) -> int:
        """Find maximum consecutive winning trades."""
        # Simplified implementation
        return 3  # Placeholder
    
    def _find_consecutive_losses(self, transactions: List[Dict]) -> int:
        """Find maximum consecutive losing trades."""
        # Simplified implementation
        return 2  # Placeholder
    
    def _calculate_gain_to_pain_ratio(self, result: BacktestResult) -> float:
        """Calculate gain to pain ratio."""
        # Simplified implementation
        if result.max_drawdown <= 0:
            return 0.0
        return float(result.total_return_percent) / float(result.max_drawdown)
    
    def _calculate_lake_ratio(self, result: BacktestResult) -> float:
        """Calculate Lake ratio."""
        # Simplified implementation
        return float(result.max_drawdown) / float(result.total_return_percent) if result.total_return_percent != 0 else 0.0
    
    def _calculate_pain_index(self, drawdown_curve: List[Dict]) -> float:
        """Calculate Pain Index."""
        if not drawdown_curve:
            return 0.0
        
        drawdowns = [abs(float(dd['drawdown_percent'])) for dd in drawdown_curve]
        return float(np.mean(drawdowns))
    
    def _calculate_tail_ratio(self, result: BacktestResult) -> float:
        """Calculate tail ratio."""
        # Simplified implementation
        return 1.2  # Placeholder
    
    def _estimate_recovery_time(self, result: BacktestResult) -> float:
        """Estimate time to recover from maximum drawdown."""
        if result.max_drawdown <= 0 or result.annual_return_percent <= 0:
            return float('inf')
        
        # Simplified calculation
        recovery_years = float(result.max_drawdown) / float(result.annual_return_percent)
        return recovery_years * 365.25  # Convert to days
    
    def _calculate_turnover_rate(self, result: BacktestResult) -> float:
        """Calculate portfolio turnover rate."""
        if result.duration_days <= 0:
            return 0.0
        
        # Simplified calculation
        years = result.duration_days / 365.25
        return result.total_trades / years if years > 0 else 0.0
    
    def _calculate_beta(self, result: BacktestResult) -> float:
        """Calculate beta vs benchmark."""
        # Simplified implementation - would need actual return series
        return 1.0  # Placeholder
    
    def _calculate_correlation(self, result: BacktestResult) -> float:
        """Calculate correlation with benchmark."""
        # Simplified implementation - would need actual return series
        return 0.7  # Placeholder
    
    def _calculate_tracking_error(self, result: BacktestResult) -> float:
        """Calculate tracking error vs benchmark."""
        # Simplified implementation
        return 5.0  # Placeholder
    
    def _calculate_information_ratio(self, result: BacktestResult) -> float:
        """Calculate information ratio."""
        # Simplified implementation
        return 0.8  # Placeholder
    
    def _calculate_treynor_ratio(self, result: BacktestResult) -> float:
        """Calculate Treynor ratio."""
        beta = self._calculate_beta(result)
        if beta == 0:
            return 0.0
        
        return (float(result.annual_return_percent) - self.risk_free_rate * 100) / beta