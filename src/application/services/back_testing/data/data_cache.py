"""
Data caching utilities for efficient data storage and retrieval.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import OrderedDict
from dataclasses import dataclass

from ..common.data_types import BaseData, SubscriptionDataConfig
from ..common.symbol import Symbol
from ..common.enums import Resolution


@dataclass
class CacheEntry:
    """
    Represents a cached data entry.
    """
    data: List[BaseData]
    timestamp: datetime
    access_count: int = 0
    last_access: datetime = None
    size_bytes: int = 0
    
    def __post_init__(self):
        if self.last_access is None:
            self.last_access = self.timestamp


class DataCache:
    """
    LRU cache for market data with automatic cleanup and statistics.
    """
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100, 
                 cleanup_interval: int = 300):
        """
        Initialize data cache.
        
        Args:
            max_size: Maximum number of cache entries
            max_memory_mb: Maximum memory usage in MB
            cleanup_interval: Cleanup interval in seconds
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cleanup_interval = cleanup_interval
        
        # Cache storage (LRU ordered)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._current_memory_usage = 0
        
        # Cleanup thread
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = False
        self._start_cleanup_thread()
    
    def get(self, symbol: Symbol, resolution: Resolution, start_time: datetime, 
           end_time: datetime) -> Optional[List[BaseData]]:
        """
        Get cached data for the specified parameters.
        """
        cache_key = self._generate_cache_key(symbol, resolution, start_time, end_time)
        
        with self._lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                
                # Move to end (most recently used)
                self._cache.move_to_end(cache_key)
                
                # Update access statistics
                entry.access_count += 1
                entry.last_access = datetime.utcnow()
                
                self._hits += 1
                return entry.data.copy()  # Return copy to prevent modification
            else:
                self._misses += 1
                return None
    
    def put(self, symbol: Symbol, resolution: Resolution, start_time: datetime, 
           end_time: datetime, data: List[BaseData]):
        """
        Cache data for the specified parameters.
        """
        if not data:
            return
        
        cache_key = self._generate_cache_key(symbol, resolution, start_time, end_time)
        
        # Estimate memory usage
        estimated_size = self._estimate_data_size(data)
        
        with self._lock:
            # Check if we need to make room
            self._ensure_capacity(estimated_size)
            
            # Create cache entry
            entry = CacheEntry(
                data=data.copy(),
                timestamp=datetime.utcnow(),
                size_bytes=estimated_size
            )
            
            # Add to cache
            self._cache[cache_key] = entry
            self._current_memory_usage += estimated_size
            
            # Move to end (most recently used)
            self._cache.move_to_end(cache_key)
    
    def invalidate(self, symbol: Symbol = None, resolution: Resolution = None):
        """
        Invalidate cache entries. If symbol is None, invalidates all entries.
        """
        with self._lock:
            if symbol is None:
                # Clear all cache
                self._current_memory_usage = 0
                self._cache.clear()
            else:
                # Invalidate entries for specific symbol
                keys_to_remove = []
                for key in self._cache.keys():
                    if key.startswith(f"{symbol}_"):
                        if resolution is None or f"_{resolution.value}_" in key:
                            keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    entry = self._cache.pop(key)
                    self._current_memory_usage -= entry.size_bytes
    
    def _generate_cache_key(self, symbol: Symbol, resolution: Resolution, 
                          start_time: datetime, end_time: datetime) -> str:
        """Generate a unique cache key."""
        return (f"{symbol}_{resolution.value}_{start_time.isoformat()}_"
                f"{end_time.isoformat()}")
    
    def _estimate_data_size(self, data: List[BaseData]) -> int:
        """Estimate memory usage of data in bytes."""
        # Rough estimation - each data point is approximately 200 bytes
        return len(data) * 200
    
    def _ensure_capacity(self, required_size: int):
        """Ensure cache has enough capacity for new data."""
        # Check size limit
        while len(self._cache) >= self.max_size:
            self._evict_oldest()
        
        # Check memory limit
        while self._current_memory_usage + required_size > self.max_memory_bytes:
            if not self._cache:
                break  # Cache is empty, can't evict more
            self._evict_oldest()
    
    def _evict_oldest(self):
        """Evict the oldest (least recently used) cache entry."""
        if self._cache:
            key, entry = self._cache.popitem(last=False)  # Remove oldest
            self._current_memory_usage -= entry.size_bytes
            self._evictions += 1
    
    def _start_cleanup_thread(self):
        """Start the background cleanup thread."""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._stop_cleanup = False
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_worker,
                daemon=True
            )
            self._cleanup_thread.start()
    
    def _cleanup_worker(self):
        """Background worker for cache cleanup."""
        while not self._stop_cleanup:
            try:
                time.sleep(self.cleanup_interval)
                self._perform_cleanup()
            except Exception as e:
                print(f"Error in cache cleanup worker: {e}")
    
    def _perform_cleanup(self):
        """Perform cache cleanup operations."""
        current_time = datetime.utcnow()
        
        with self._lock:
            # Remove entries older than 1 hour that haven't been accessed recently
            keys_to_remove = []
            
            for key, entry in self._cache.items():
                age = current_time - entry.timestamp
                time_since_access = current_time - entry.last_access
                
                # Remove if older than 1 hour and not accessed in 30 minutes
                if age > timedelta(hours=1) and time_since_access > timedelta(minutes=30):
                    keys_to_remove.append(key)
                # Or if very old (> 24 hours)
                elif age > timedelta(hours=24):
                    keys_to_remove.append(key)
            
            # Remove identified entries
            for key in keys_to_remove:
                entry = self._cache.pop(key)
                self._current_memory_usage -= entry.size_bytes
                self._evictions += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'entries': len(self._cache),
                'memory_usage_mb': self._current_memory_usage / (1024 * 1024),
                'memory_usage_percent': (self._current_memory_usage / self.max_memory_bytes * 100),
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'evictions': self._evictions,
                'max_size': self.max_size,
                'max_memory_mb': self.max_memory_bytes / (1024 * 1024)
            }
    
    def get_cache_info(self) -> List[Dict[str, Any]]:
        """Get detailed information about cache entries."""
        with self._lock:
            cache_info = []
            
            for key, entry in self._cache.items():
                cache_info.append({
                    'key': key,
                    'data_points': len(entry.data),
                    'size_mb': entry.size_bytes / (1024 * 1024),
                    'created': entry.timestamp,
                    'last_access': entry.last_access,
                    'access_count': entry.access_count,
                    'age_minutes': (datetime.utcnow() - entry.timestamp).total_seconds() / 60
                })
            
            return cache_info
    
    def warm_up(self, symbols: List[Symbol], resolution: Resolution, 
               start_time: datetime, end_time: datetime, data_provider):
        """
        Warm up the cache by pre-loading data for specified symbols.
        """
        for symbol in symbols:
            try:
                # Check if data is already cached
                cached_data = self.get(symbol, resolution, start_time, end_time)
                
                if cached_data is None:
                    # Fetch data from provider and cache it
                    data = data_provider.get_history(symbol, start_time, end_time, resolution)
                    if data:
                        self.put(symbol, resolution, start_time, end_time, data)
                        
            except Exception as e:
                print(f"Error warming up cache for {symbol}: {e}")
    
    def resize(self, new_max_size: int = None, new_max_memory_mb: int = None):
        """
        Resize the cache limits.
        """
        with self._lock:
            if new_max_size is not None:
                self.max_size = new_max_size
                
                # Evict entries if new size is smaller
                while len(self._cache) > self.max_size:
                    self._evict_oldest()
            
            if new_max_memory_mb is not None:
                self.max_memory_bytes = new_max_memory_mb * 1024 * 1024
                
                # Evict entries if new memory limit is smaller
                while self._current_memory_usage > self.max_memory_bytes:
                    if not self._cache:
                        break
                    self._evict_oldest()
    
    def export_statistics(self) -> str:
        """Export cache statistics as a formatted string."""
        stats = self.get_statistics()
        
        return f"""
Cache Statistics:
================
Entries: {stats['entries']}/{stats['max_size']}
Memory Usage: {stats['memory_usage_mb']:.2f}/{stats['max_memory_mb']:.2f} MB ({stats['memory_usage_percent']:.1f}%)
Hit Rate: {stats['hit_rate']:.1f}% ({stats['hits']} hits, {stats['misses']} misses)
Evictions: {stats['evictions']}
        """.strip()
    
    def dispose(self):
        """Clean up cache resources."""
        self._stop_cleanup = True
        
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5.0)
        
        with self._lock:
            self._cache.clear()
            self._current_memory_usage = 0


class SymbolDataCache:
    """
    Specialized cache for symbol-specific data with different retention policies.
    """
    
    def __init__(self):
        self._caches: Dict[Tuple[Symbol, Resolution], DataCache] = {}
        self._global_lock = threading.RLock()
    
    def get_cache(self, symbol: Symbol, resolution: Resolution) -> DataCache:
        """Get or create a cache for a specific symbol and resolution."""
        cache_key = (symbol, resolution)
        
        with self._global_lock:
            if cache_key not in self._caches:
                # Create cache with resolution-specific settings
                if resolution == Resolution.TICK:
                    # Smaller cache for tick data (high frequency)
                    cache = DataCache(max_size=100, max_memory_mb=50, cleanup_interval=60)
                elif resolution in [Resolution.SECOND, Resolution.MINUTE]:
                    # Medium cache for intraday data
                    cache = DataCache(max_size=300, max_memory_mb=100, cleanup_interval=300)
                else:
                    # Larger cache for daily+ data
                    cache = DataCache(max_size=1000, max_memory_mb=200, cleanup_interval=600)
                
                self._caches[cache_key] = cache
            
            return self._caches[cache_key]
    
    def get_data(self, symbol: Symbol, resolution: Resolution, start_time: datetime, 
                end_time: datetime) -> Optional[List[BaseData]]:
        """Get cached data for symbol and resolution."""
        cache = self.get_cache(symbol, resolution)
        return cache.get(symbol, resolution, start_time, end_time)
    
    def put_data(self, symbol: Symbol, resolution: Resolution, start_time: datetime, 
                end_time: datetime, data: List[BaseData]):
        """Cache data for symbol and resolution."""
        cache = self.get_cache(symbol, resolution)
        cache.put(symbol, resolution, start_time, end_time, data)
    
    def invalidate_symbol(self, symbol: Symbol, resolution: Resolution = None):
        """Invalidate all cached data for a symbol."""
        with self._global_lock:
            if resolution is not None:
                # Invalidate specific resolution
                cache_key = (symbol, resolution)
                if cache_key in self._caches:
                    self._caches[cache_key].invalidate(symbol)
            else:
                # Invalidate all resolutions for symbol
                keys_to_invalidate = [key for key in self._caches.keys() if key[0] == symbol]
                for key in keys_to_invalidate:
                    self._caches[key].invalidate(symbol)
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """Get statistics for all caches."""
        with self._global_lock:
            total_entries = 0
            total_memory = 0
            total_hits = 0
            total_misses = 0
            
            cache_details = []
            
            for (symbol, resolution), cache in self._caches.items():
                stats = cache.get_statistics()
                
                total_entries += stats['entries']
                total_memory += stats['memory_usage_mb']
                total_hits += stats['hits']
                total_misses += stats['misses']
                
                cache_details.append({
                    'symbol': str(symbol),
                    'resolution': resolution.value,
                    'entries': stats['entries'],
                    'memory_mb': stats['memory_usage_mb'],
                    'hit_rate': stats['hit_rate']
                })
            
            total_requests = total_hits + total_misses
            global_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'total_caches': len(self._caches),
                'total_entries': total_entries,
                'total_memory_mb': total_memory,
                'global_hit_rate': global_hit_rate,
                'cache_details': cache_details
            }
    
    def dispose(self):
        """Dispose all caches."""
        with self._global_lock:
            for cache in self._caches.values():
                cache.dispose()
            self._caches.clear()