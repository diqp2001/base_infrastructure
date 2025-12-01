"""
Performance metrics calculation utilities.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional


class PerformanceCalculator:
    """Calculate trading strategy performance metrics."""
    
    @staticmethod
    def calculate_returns_metrics(returns: pd.Series) -> Dict[str, float]:
        """Calculate comprehensive returns-based metrics."""
        if len(returns) == 0:
            return {}
        
        # Basic return metrics
        total_return = (1 + returns).prod() - 1
        annualized_return = (1 + returns).prod() ** (252 / len(returns)) - 1
        volatility = returns.std() * np.sqrt(252)
        
        # Risk-adjusted metrics
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        # Drawdown metrics
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = cumulative_returns / rolling_max - 1
        max_drawdown = drawdowns.min()
        
        # Win rate
        win_rate = (returns > 0).mean()
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'calmar_ratio': annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        }