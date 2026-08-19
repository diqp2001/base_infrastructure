"""
Standalone performance metrics calculation for backtesting results.
"""

import logging
import numpy as np
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def calculate_performance_metrics(
    daily_returns: List[float],
    initial_capital: float,
    final_value: float,
) -> Dict[str, Any]:
    """
    Calculate comprehensive performance metrics from a daily returns series.

    Args:
        daily_returns: List of per-day portfolio returns (fractional, e.g. 0.01 = +1%)
        initial_capital: Portfolio value at the start of the period
        final_value: Portfolio value at the end of the period

    Returns:
        Dict with total_return, annualized_return, volatility, sharpe_ratio,
        max_drawdown, win_rate, total_trading_days, best_day, worst_day.
        Returns {'error': <message>} on failure.
    """
    try:
        if not daily_returns:
            return {'error': 'No returns data available'}

        returns_array = np.array(daily_returns)

        total_return = (final_value - initial_capital) / initial_capital
        annualized_return = (1 + total_return) ** (252 / len(daily_returns)) - 1

        volatility = np.std(returns_array) * np.sqrt(252)
        sharpe_ratio = annualized_return / volatility if volatility != 0 else 0.0

        cumulative_returns = np.cumprod(1 + returns_array)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = float(np.min(drawdowns))

        positive_days = np.sum(returns_array > 0)
        win_rate = float(positive_days / len(returns_array))

        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trading_days': len(daily_returns),
            'best_day': float(np.max(returns_array)),
            'worst_day': float(np.min(returns_array)),
        }

    except Exception as e:
        logger.error(f"Error calculating performance metrics: {e}")
        return {
            'error': str(e),
            'total_return': (final_value - initial_capital) / initial_capital,
        }
