"""
Engine module for QuantConnect Lean Python implementation.
Core backtesting and live trading engine with handler-based architecture.
"""

from .interfaces import (
    IEngine, IDataFeed, ITransactionHandler, IResultHandler, 
    ISetupHandler, IRealTimeHandler, IAlgorithmHandler
)
from .lean_engine import LeanEngine
from .base_engine import BaseEngine
from .data_feeds import FileSystemDataFeed, LiveDataFeed, BacktestingDataFeed
from .transaction_handlers import BacktestingTransactionHandler, BrokerageTransactionHandler
from .result_handlers import BacktestingResultHandler, LiveTradingResultHandler
from .setup_handlers import ConsoleSetupHandler, BacktestingSetupHandler
from .realtime_handlers import BacktestingRealTimeHandler, LiveTradingRealTimeHandler
from .algorithm_handlers import AlgorithmHandler
from .engine_node_packet import EngineNodePacket
from .enums import EngineType, HandlerType

__all__ = [
    # Core Interfaces
    'IEngine', 'IDataFeed', 'ITransactionHandler', 'IResultHandler',
    'ISetupHandler', 'IRealTimeHandler', 'IAlgorithmHandler',
    
    # Main Engine Classes
    'LeanEngine', 'BaseEngine',
    
    # Data Feed Handlers
    'FileSystemDataFeed', 'LiveDataFeed', 'BacktestingDataFeed',
    
    # Transaction Handlers
    'BacktestingTransactionHandler', 'BrokerageTransactionHandler',
    
    # Result Handlers
    'BacktestingResultHandler', 'LiveTradingResultHandler',
    
    # Setup Handlers
    'ConsoleSetupHandler', 'BacktestingSetupHandler',
    
    # Real-time Handlers
    'BacktestingRealTimeHandler', 'LiveTradingRealTimeHandler',
    
    # Algorithm Handlers
    'AlgorithmHandler',
    
    # Configuration
    'EngineNodePacket', 'EngineType', 'HandlerType',
]