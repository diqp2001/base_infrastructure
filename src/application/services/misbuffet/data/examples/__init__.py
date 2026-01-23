"""
Examples package for market data services.
Contains example implementations showing how to use MarketDataService and MarketDataHistoryService.
"""

from .engine_loop_example import TradingEngine, MockAlgorithm
from .algorithm_usage_example import (
    BaseAlgorithm, 
    MovingAverageAlgorithm, 
    MeanReversionAlgorithm, 
    PairsTradingAlgorithm
)

__all__ = [
    'TradingEngine',
    'MockAlgorithm',
    'BaseAlgorithm',
    'MovingAverageAlgorithm',
    'MeanReversionAlgorithm',
    'PairsTradingAlgorithm'
]