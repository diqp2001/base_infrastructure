"""
Data queue handlers for different data sources.
"""

import random
import time
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from queue import Queue, Empty
from decimal import Decimal

from ..common.data_types import BaseData, TradeBar, QuoteBar, Tick
from ..common.symbol import Symbol
from ..common.enums import TickType, SecurityType, Market
from ..common.time_utils import Time


class DataQueueHandler(ABC):
    """
    Abstract base class for data queue handlers.
    Handles real-time data streaming from various sources.
    """
    
    def __init__(self):
        self._is_connected = False
        self._subscribed_symbols: List[Symbol] = []
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the data queue handler."""
        pass
    
    @abstractmethod
    def subscribe(self, symbols: List[Symbol]) -> bool:
        """Subscribe to data for the given symbols."""
        pass
    
    @abstractmethod
    def unsubscribe(self, symbols: List[Symbol]) -> bool:
        """Unsubscribe from data for the given symbols."""
        pass
    
    @abstractmethod
    def get_next_ticks(self) -> List[BaseData]:
        """Get the next batch of ticks."""
        pass
    
    def is_connected(self) -> bool:
        """Check if the handler is connected."""
        return self._is_connected
    
    def get_subscribed_symbols(self) -> List[Symbol]:
        """Get list of subscribed symbols."""
        return self._subscribed_symbols.copy()
    
    def dispose(self):
        """Clean up resources."""
        self._is_connected = False
        self._subscribed_symbols.clear()


class FakeDataQueue(DataQueueHandler):
    """
    Fake data queue handler for testing and simulation.
    Generates random market data.
    """
    
    def __init__(self, seed: int = None):
        super().__init__()
        if seed is not None:
            random.seed(seed)
        
        self._data_queue: Queue = Queue()
        self._generator_thread: Optional[threading.Thread] = None
        self._stop_generation = False
        
        # Price tracking for realistic data generation
        self._last_prices: Dict[Symbol, Decimal] = {}
        self._price_volatility = Decimal('0.001')  # 0.1% volatility
        self._generation_interval = 0.1  # 100ms between data points
    
    def initialize(self) -> bool:
        """Initialize the fake data queue."""
        try:
            self._is_connected = True
            return True
        except Exception as e:
            print(f"Failed to initialize fake data queue: {e}")
            return False
    
    def subscribe(self, symbols: List[Symbol]) -> bool:
        """Subscribe to fake data for symbols."""
        try:
            for symbol in symbols:
                if symbol not in self._subscribed_symbols:
                    self._subscribed_symbols.append(symbol)
                    # Initialize with a random starting price
                    self._last_prices[symbol] = self._generate_initial_price(symbol)
            
            # Start data generation if not already running
            if not self._generator_thread or not self._generator_thread.is_alive():
                self._start_data_generation()
            
            return True
            
        except Exception as e:
            print(f"Failed to subscribe to symbols: {e}")
            return False
    
    def unsubscribe(self, symbols: List[Symbol]) -> bool:
        """Unsubscribe from fake data for symbols."""
        try:
            for symbol in symbols:
                if symbol in self._subscribed_symbols:
                    self._subscribed_symbols.remove(symbol)
                    self._last_prices.pop(symbol, None)
            
            # Stop generation if no symbols left
            if not self._subscribed_symbols:
                self._stop_data_generation()
            
            return True
            
        except Exception as e:
            print(f"Failed to unsubscribe from symbols: {e}")
            return False
    
    def get_next_ticks(self) -> List[BaseData]:
        """Get the next batch of fake ticks."""
        ticks = []
        
        # Get all available ticks from queue
        while not self._data_queue.empty():
            try:
                tick = self._data_queue.get_nowait()
                ticks.append(tick)
                
                # Limit batch size
                if len(ticks) >= 100:
                    break
                    
            except Empty:
                break
        
        return ticks
    
    def _generate_initial_price(self, symbol: Symbol) -> Decimal:
        """Generate initial price based on symbol type."""
        if symbol.security_type == SecurityType.EQUITY:
            return Decimal(str(random.uniform(10.0, 500.0)))
        elif symbol.security_type == SecurityType.FOREX:
            return Decimal(str(random.uniform(0.5, 2.0)))
        elif symbol.security_type == SecurityType.CRYPTO:
            return Decimal(str(random.uniform(100.0, 50000.0)))
        else:
            return Decimal(str(random.uniform(50.0, 200.0)))
    
    def _start_data_generation(self):
        """Start the data generation thread."""
        if self._generator_thread is None or not self._generator_thread.is_alive():
            self._stop_generation = False
            self._generator_thread = threading.Thread(
                target=self._data_generation_worker,
                daemon=True
            )
            self._generator_thread.start()
    
    def _stop_data_generation(self):
        """Stop the data generation thread."""
        self._stop_generation = True
    
    def _data_generation_worker(self):
        """Worker thread for generating fake data."""
        while not self._stop_generation and self._is_connected:
            try:
                for symbol in self._subscribed_symbols.copy():
                    # Generate random data for each symbol
                    data_points = self._generate_data_for_symbol(symbol)
                    
                    for data_point in data_points:
                        if not self._data_queue.full():
                            self._data_queue.put(data_point)
                
                # Sleep between generations
                time.sleep(self._generation_interval)
                
            except Exception as e:
                print(f"Error in data generation worker: {e}")
                time.sleep(1.0)  # Longer sleep on error
    
    def _generate_data_for_symbol(self, symbol: Symbol) -> List[BaseData]:
        """Generate fake data for a specific symbol."""
        data_points = []
        current_time = Time.utc_now()
        
        # Update last price with random walk
        if symbol in self._last_prices:
            last_price = self._last_prices[symbol]
            
            # Random walk with mean reversion
            change_percent = Decimal(str(random.gauss(0, float(self._price_volatility))))
            new_price = last_price * (1 + change_percent)
            
            # Ensure price doesn't go negative
            new_price = max(new_price, last_price * Decimal('0.5'))
            
            self._last_prices[symbol] = new_price
        else:
            new_price = self._generate_initial_price(symbol)
            self._last_prices[symbol] = new_price
        
        # Generate different types of data based on random choice
        data_type = random.choice(['tick', 'quote', 'trade_bar'])
        
        if data_type == 'tick':
            # Generate tick data
            tick = Tick(
                symbol=symbol,
                time=current_time,
                value=new_price,
                tick_type=TickType.TRADE,
                quantity=random.randint(100, 10000),
                exchange="FAKE"
            )
            data_points.append(tick)
            
        elif data_type == 'quote':
            # Generate quote bar
            spread = new_price * Decimal('0.001')  # 0.1% spread
            bid_price = new_price - spread / 2
            ask_price = new_price + spread / 2
            
            # Note: QuoteBar creation would need Bar objects for bid/ask
            # For simplicity, creating a tick with bid/ask info
            quote_tick = Tick(
                symbol=symbol,
                time=current_time,
                value=new_price,
                tick_type=TickType.QUOTE,
                bid_price=bid_price,
                ask_price=ask_price,
                bid_size=random.randint(100, 1000),
                ask_size=random.randint(100, 1000)
            )
            data_points.append(quote_tick)
            
        else:
            # Generate trade bar (1-minute bar)
            volatility = new_price * self._price_volatility
            
            open_price = new_price
            high_price = new_price + abs(Decimal(str(random.gauss(0, float(volatility)))))
            low_price = new_price - abs(Decimal(str(random.gauss(0, float(volatility)))))
            close_price = new_price
            volume = random.randint(1000, 100000)
            
            trade_bar = TradeBar(
                symbol=symbol,
                time=current_time,
                value=close_price,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume
            )
            data_points.append(trade_bar)
        
        return data_points
    
    def set_volatility(self, volatility: float):
        """Set the price volatility for data generation."""
        self._price_volatility = Decimal(str(volatility))
    
    def set_generation_interval(self, interval: float):
        """Set the data generation interval in seconds."""
        self._generation_interval = interval
    
    def dispose(self):
        """Clean up resources."""
        self._stop_data_generation()
        
        # Wait for generator thread to finish
        if self._generator_thread and self._generator_thread.is_alive():
            self._generator_thread.join(timeout=5.0)
        
        super().dispose()


class WebSocketDataQueue(DataQueueHandler):
    """
    Data queue handler for WebSocket connections.
    Base class for WebSocket-based data feeds.
    """
    
    def __init__(self, url: str, api_key: str = None):
        super().__init__()
        self.url = url
        self.api_key = api_key
        self._websocket = None
        self._data_queue: Queue = Queue()
        self._connection_thread: Optional[threading.Thread] = None
        self._stop_connection = False
    
    def initialize(self) -> bool:
        """Initialize the WebSocket connection."""
        try:
            # This would be implemented with a real WebSocket library
            # For now, just simulate connection
            self._is_connected = True
            self._start_connection_thread()
            return True
            
        except Exception as e:
            print(f"Failed to initialize WebSocket connection: {e}")
            return False
    
    def subscribe(self, symbols: List[Symbol]) -> bool:
        """Subscribe to symbols via WebSocket."""
        try:
            for symbol in symbols:
                if symbol not in self._subscribed_symbols:
                    self._subscribed_symbols.append(symbol)
                    # Send subscription message via WebSocket
                    self._send_subscribe_message(symbol)
            
            return True
            
        except Exception as e:
            print(f"Failed to subscribe via WebSocket: {e}")
            return False
    
    def unsubscribe(self, symbols: List[Symbol]) -> bool:
        """Unsubscribe from symbols via WebSocket."""
        try:
            for symbol in symbols:
                if symbol in self._subscribed_symbols:
                    self._subscribed_symbols.remove(symbol)
                    # Send unsubscribe message via WebSocket
                    self._send_unsubscribe_message(symbol)
            
            return True
            
        except Exception as e:
            print(f"Failed to unsubscribe via WebSocket: {e}")
            return False
    
    def get_next_ticks(self) -> List[BaseData]:
        """Get next ticks from WebSocket queue."""
        ticks = []
        
        while not self._data_queue.empty():
            try:
                tick = self._data_queue.get_nowait()
                ticks.append(tick)
                
                if len(ticks) >= 100:
                    break
                    
            except Empty:
                break
        
        return ticks
    
    def _start_connection_thread(self):
        """Start the WebSocket connection thread."""
        if self._connection_thread is None or not self._connection_thread.is_alive():
            self._stop_connection = False
            self._connection_thread = threading.Thread(
                target=self._connection_worker,
                daemon=True
            )
            self._connection_thread.start()
    
    def _connection_worker(self):
        """WebSocket connection worker."""
        while not self._stop_connection:
            try:
                # This would handle WebSocket messages
                # For simulation, just sleep
                time.sleep(0.1)
                
            except Exception as e:
                print(f"WebSocket connection error: {e}")
                time.sleep(5.0)  # Retry after 5 seconds
    
    def _send_subscribe_message(self, symbol: Symbol):
        """Send subscription message via WebSocket."""
        # This would send actual subscription message
        pass
    
    def _send_unsubscribe_message(self, symbol: Symbol):
        """Send unsubscription message via WebSocket."""
        # This would send actual unsubscription message
        pass
    
    def _handle_websocket_message(self, message: Dict[str, Any]):
        """Handle incoming WebSocket message."""
        # This would parse WebSocket messages and create BaseData objects
        pass
    
    def dispose(self):
        """Clean up WebSocket resources."""
        self._stop_connection = True
        
        if self._connection_thread and self._connection_thread.is_alive():
            self._connection_thread.join(timeout=5.0)
        
        if self._websocket:
            # Close WebSocket connection
            pass
        
        super().dispose()


class RestApiDataQueue(DataQueueHandler):
    """
    Data queue handler for REST API polling.
    Polls REST endpoints for market data.
    """
    
    def __init__(self, base_url: str, api_key: str = None, poll_interval: float = 1.0):
        super().__init__()
        self.base_url = base_url
        self.api_key = api_key
        self.poll_interval = poll_interval
        
        self._data_queue: Queue = Queue()
        self._polling_thread: Optional[threading.Thread] = None
        self._stop_polling = False
        
        # Track last request times to avoid rate limiting
        self._last_request_times: Dict[Symbol, datetime] = {}
        self._min_request_interval = timedelta(seconds=1)
    
    def initialize(self) -> bool:
        """Initialize the REST API data queue."""
        try:
            # Test API connection
            if self._test_connection():
                self._is_connected = True
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Failed to initialize REST API connection: {e}")
            return False
    
    def subscribe(self, symbols: List[Symbol]) -> bool:
        """Subscribe to symbols for REST API polling."""
        try:
            for symbol in symbols:
                if symbol not in self._subscribed_symbols:
                    self._subscribed_symbols.append(symbol)
            
            # Start polling if not already running
            if not self._polling_thread or not self._polling_thread.is_alive():
                self._start_polling()
            
            return True
            
        except Exception as e:
            print(f"Failed to subscribe to REST API: {e}")
            return False
    
    def unsubscribe(self, symbols: List[Symbol]) -> bool:
        """Unsubscribe from symbols."""
        try:
            for symbol in symbols:
                if symbol in self._subscribed_symbols:
                    self._subscribed_symbols.remove(symbol)
                    self._last_request_times.pop(symbol, None)
            
            # Stop polling if no symbols left
            if not self._subscribed_symbols:
                self._stop_polling_thread()
            
            return True
            
        except Exception as e:
            print(f"Failed to unsubscribe from REST API: {e}")
            return False
    
    def get_next_ticks(self) -> List[BaseData]:
        """Get next ticks from REST API queue."""
        ticks = []
        
        while not self._data_queue.empty():
            try:
                tick = self._data_queue.get_nowait()
                ticks.append(tick)
                
                if len(ticks) >= 50:  # Smaller batch size for REST API
                    break
                    
            except Empty:
                break
        
        return ticks
    
    def _test_connection(self) -> bool:
        """Test the REST API connection."""
        # This would make a test API call
        return True  # Simulate successful connection
    
    def _start_polling(self):
        """Start the REST API polling thread."""
        if self._polling_thread is None or not self._polling_thread.is_alive():
            self._stop_polling = False
            self._polling_thread = threading.Thread(
                target=self._polling_worker,
                daemon=True
            )
            self._polling_thread.start()
    
    def _stop_polling_thread(self):
        """Stop the polling thread."""
        self._stop_polling = True
    
    def _polling_worker(self):
        """REST API polling worker."""
        while not self._stop_polling and self._is_connected:
            try:
                current_time = datetime.utcnow()
                
                for symbol in self._subscribed_symbols.copy():
                    # Check if enough time has passed since last request
                    last_request = self._last_request_times.get(symbol, datetime.min)
                    
                    if current_time - last_request >= self._min_request_interval:
                        data = self._fetch_symbol_data(symbol)
                        if data:
                            self._data_queue.put(data)
                        
                        self._last_request_times[symbol] = current_time
                
                # Sleep between polling cycles
                time.sleep(self.poll_interval)
                
            except Exception as e:
                print(f"Error in REST API polling worker: {e}")
                time.sleep(5.0)  # Longer sleep on error
    
    def _fetch_symbol_data(self, symbol: Symbol) -> Optional[BaseData]:
        """Fetch data for a symbol from REST API."""
        try:
            # This would make actual REST API call
            # For simulation, generate fake data
            current_time = Time.utc_now()
            price = Decimal(str(random.uniform(50.0, 200.0)))
            
            return Tick(
                symbol=symbol,
                time=current_time,
                value=price,
                tick_type=TickType.TRADE,
                quantity=random.randint(100, 1000),
                exchange="REST_API"
            )
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
    
    def dispose(self):
        """Clean up REST API resources."""
        self._stop_polling_thread()
        
        if self._polling_thread and self._polling_thread.is_alive():
            self._polling_thread.join(timeout=5.0)
        
        super().dispose()