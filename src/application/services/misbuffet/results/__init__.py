"""
Results handling for misbuffet backtesting.
Provides result processing, storage, and analysis capabilities.
"""

from .result_handler import BacktestResultHandler, BacktestResult
from .performance_analyzer import PerformanceAnalyzer
from .result_storage import ResultStorage

__all__ = [
    'BacktestResultHandler',
    'BacktestResult',
    'PerformanceAnalyzer', 
    'ResultStorage',
]