"""
Data module for QuantConnect Lean Python implementation.
Handles data acquisition, formatting, and consumption of market data.
"""

from .data_feed import DataFeed, LiveTradingDataFeed, FileSystemDataFeed
from .subscription_manager import SubscriptionManager, SubscriptionDataConfig
from .data_reader import (
    BaseDataReader, LeanDataReader, CsvDataReader, AlphaStreamsDataReader
)
from .history_provider import (
    HistoryProvider, FileSystemHistoryProvider, BrokerageHistoryProvider,
    SubscriptionHistoryProvider
)
from .data_manager import DataManager
from .data_queue_handler import DataQueueHandler, FakeDataQueue
from .data_normalization import DataNormalizationHelper
from .data_cache import DataCache
from .file_format import FileFormat

# New DDD-oriented services
from .market_data_service import MarketDataService
from .market_data_history_service import MarketDataHistoryService, Frontier
from .data_loader import DataLoader, DataConfiguration, DataServices

__all__ = [
    # Data Feeds
    'DataFeed', 'LiveTradingDataFeed', 'FileSystemDataFeed',
    
    # Subscription Management
    'SubscriptionManager', 'SubscriptionDataConfig',
    
    # Data Readers
    'BaseDataReader', 'LeanDataReader', 'CsvDataReader', 'AlphaStreamsDataReader',
    
    # History Providers
    'HistoryProvider', 'FileSystemHistoryProvider', 'BrokerageHistoryProvider',
    'SubscriptionHistoryProvider',
    
    # Data Management
    'DataManager', 'DataQueueHandler', 'FakeDataQueue',
    
    # DDD-oriented Services
    'MarketDataService', 'MarketDataHistoryService', 'Frontier',
    'DataLoader', 'DataConfiguration', 'DataServices',
    
    # Utilities
    'DataNormalizationHelper', 'DataCache', 'FileFormat',
]