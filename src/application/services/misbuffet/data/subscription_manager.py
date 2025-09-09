"""
Subscription management for data feeds.
"""

from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass

from ..common.data_types import SubscriptionDataConfig, BaseData
from ..common.symbol import Symbol
from ..common.enums import Resolution, SecurityType
from ..common.time_utils import Time


class SubscriptionManager:
    """
    Manages data subscriptions and configurations.
    """
    
    def __init__(self):
        self._subscriptions: Dict[str, SubscriptionDataConfig] = {}
        self._symbol_to_configs: Dict[Symbol, List[SubscriptionDataConfig]] = {}
        self._active_subscriptions: Set[str] = set()
        
        # Market hours database for subscription filtering
        self._market_hours_db = Time().get_market_hours_database()
    
    def add_subscription(self, config: SubscriptionDataConfig) -> bool:
        """Add a subscription configuration."""
        subscription_id = config.sid
        
        if subscription_id in self._subscriptions:
            # Subscription already exists
            return False
        
        # Store the configuration
        self._subscriptions[subscription_id] = config
        self._active_subscriptions.add(subscription_id)
        
        # Index by symbol
        if config.symbol not in self._symbol_to_configs:
            self._symbol_to_configs[config.symbol] = []
        self._symbol_to_configs[config.symbol].append(config)
        
        return True
    
    def remove_subscription(self, config: SubscriptionDataConfig) -> bool:
        """Remove a subscription configuration."""
        subscription_id = config.sid
        
        if subscription_id not in self._subscriptions:
            return False
        
        # Remove from main storage
        del self._subscriptions[subscription_id]
        self._active_subscriptions.discard(subscription_id)
        
        # Remove from symbol index
        if config.symbol in self._symbol_to_configs:
            configs = self._symbol_to_configs[config.symbol]
            configs = [c for c in configs if c.sid != subscription_id]
            
            if configs:
                self._symbol_to_configs[config.symbol] = configs
            else:
                del self._symbol_to_configs[config.symbol]
        
        return True
    
    def remove_symbol(self, symbol: Symbol) -> bool:
        """Remove all subscriptions for a symbol."""
        if symbol not in self._symbol_to_configs:
            return False
        
        configs = self._symbol_to_configs[symbol].copy()
        for config in configs:
            self.remove_subscription(config)
        
        return True
    
    def get_subscription(self, subscription_id: str) -> Optional[SubscriptionDataConfig]:
        """Get a subscription by ID."""
        return self._subscriptions.get(subscription_id)
    
    def get_subscriptions(self) -> List[SubscriptionDataConfig]:
        """Get all active subscriptions."""
        return [self._subscriptions[sid] for sid in self._active_subscriptions]
    
    def get_subscriptions_for_symbol(self, symbol: Symbol) -> List[SubscriptionDataConfig]:
        """Get all subscriptions for a specific symbol."""
        return self._symbol_to_configs.get(symbol, [])
    
    def get_symbols(self) -> List[Symbol]:
        """Get all subscribed symbols."""
        return list(self._symbol_to_configs.keys())
    
    def is_subscribed(self, symbol: Symbol, resolution: Resolution = None) -> bool:
        """Check if a symbol is subscribed (optionally at a specific resolution)."""
        if symbol not in self._symbol_to_configs:
            return False
        
        if resolution is None:
            return True
        
        configs = self._symbol_to_configs[symbol]
        return any(config.resolution == resolution for config in configs)
    
    def should_process_data(self, data: BaseData, current_time: datetime) -> bool:
        """
        Determine if data should be processed based on subscription configuration.
        """
        symbol = data.symbol
        configs = self.get_subscriptions_for_symbol(symbol)
        
        if not configs:
            return False
        
        # Check each subscription configuration
        for config in configs:
            if self._should_process_for_config(data, config, current_time):
                return True
        
        return False
    
    def _should_process_for_config(self, data: BaseData, config: SubscriptionDataConfig, 
                                  current_time: datetime) -> bool:
        """Check if data should be processed for a specific configuration."""
        
        # Check data type
        if not isinstance(data, config.data_type):
            return False
        
        # Check market hours if configured
        if not config.extended_market_hours:
            market_open = self._market_hours_db.is_market_open(
                config.market, 
                config.symbol.security_type.value,
                data.time
            )
            if not market_open:
                return False
        
        # Check if data is too old (for live trading)
        time_diff = current_time - data.time
        if time_diff.total_seconds() > 300:  # 5 minutes threshold
            return False
        
        return True
    
    def get_subscription_configs_for_processing(self, current_time: datetime) -> List[SubscriptionDataConfig]:
        """Get subscription configurations that should be processed at the current time."""
        active_configs = []
        
        for config in self.get_subscriptions():
            # Check if market is open for this subscription
            if config.extended_market_hours:
                # Always process if extended hours are enabled
                active_configs.append(config)
            else:
                # Check market hours
                market_open = self._market_hours_db.is_market_open(
                    config.market,
                    config.symbol.security_type.value,
                    current_time
                )
                if market_open:
                    active_configs.append(config)
        
        return active_configs
    
    def filter_data_by_subscriptions(self, data_points: List[BaseData], 
                                   current_time: datetime) -> List[BaseData]:
        """Filter data points based on active subscriptions."""
        filtered_data = []
        
        for data_point in data_points:
            if self.should_process_data(data_point, current_time):
                filtered_data.append(data_point)
        
        return filtered_data
    
    def update_subscription_config(self, subscription_id: str, **updates) -> bool:
        """Update a subscription configuration."""
        if subscription_id not in self._subscriptions:
            return False
        
        config = self._subscriptions[subscription_id]
        
        # Create updated configuration
        updated_config = config.clone()
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(updated_config, key):
                setattr(updated_config, key, value)
        
        # Replace the configuration
        self._subscriptions[subscription_id] = updated_config
        
        # Update symbol index
        symbol_configs = self._symbol_to_configs.get(config.symbol, [])
        for i, cfg in enumerate(symbol_configs):
            if cfg.sid == subscription_id:
                symbol_configs[i] = updated_config
                break
        
        return True
    
    def pause_subscription(self, subscription_id: str) -> bool:
        """Pause a subscription (remove from active set)."""
        if subscription_id in self._subscriptions:
            self._active_subscriptions.discard(subscription_id)
            return True
        return False
    
    def resume_subscription(self, subscription_id: str) -> bool:
        """Resume a paused subscription."""
        if subscription_id in self._subscriptions:
            self._active_subscriptions.add(subscription_id)
            return True
        return False
    
    def get_subscription_statistics(self) -> Dict[str, Any]:
        """Get statistics about current subscriptions."""
        total_subscriptions = len(self._subscriptions)
        active_subscriptions = len(self._active_subscriptions)
        paused_subscriptions = total_subscriptions - active_subscriptions
        
        # Count by resolution
        resolution_counts = {}
        for config in self._subscriptions.values():
            res = config.resolution.value
            resolution_counts[res] = resolution_counts.get(res, 0) + 1
        
        # Count by security type
        security_type_counts = {}
        for config in self._subscriptions.values():
            sec_type = config.symbol.security_type.value
            security_type_counts[sec_type] = security_type_counts.get(sec_type, 0) + 1
        
        # Count by market
        market_counts = {}
        for config in self._subscriptions.values():
            market = config.market
            market_counts[market] = market_counts.get(market, 0) + 1
        
        return {
            'total_subscriptions': total_subscriptions,
            'active_subscriptions': active_subscriptions,
            'paused_subscriptions': paused_subscriptions,
            'unique_symbols': len(self._symbol_to_configs),
            'resolution_breakdown': resolution_counts,
            'security_type_breakdown': security_type_counts,
            'market_breakdown': market_counts
        }
    
    def clear(self):
        """Clear all subscriptions."""
        self._subscriptions.clear()
        self._symbol_to_configs.clear()
        self._active_subscriptions.clear()
    
    def __len__(self) -> int:
        """Get the number of active subscriptions."""
        return len(self._active_subscriptions)
    
    def __contains__(self, subscription_id: str) -> bool:
        """Check if a subscription ID exists."""
        return subscription_id in self._subscriptions
    
    def __str__(self) -> str:
        """String representation of the subscription manager."""
        stats = self.get_subscription_statistics()
        return (f"SubscriptionManager(active={stats['active_subscriptions']}, "
                f"symbols={stats['unique_symbols']})")


@dataclass
class SubscriptionRequest:
    """
    Represents a request to add or modify a subscription.
    """
    symbol: Symbol
    resolution: Resolution
    data_type: type = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    fill_forward: bool = True
    extended_market_hours: bool = False
    is_internal_feed: bool = False
    
    def to_config(self) -> SubscriptionDataConfig:
        """Convert this request to a subscription configuration."""
        from ..common.data_types import TradeBar
        
        data_type = self.data_type or TradeBar
        
        return SubscriptionDataConfig(
            symbol=self.symbol,
            data_type=data_type,
            resolution=self.resolution,
            time_zone="UTC",
            market=self.symbol.market.value,
            fill_forward=self.fill_forward,
            extended_market_hours=self.extended_market_hours,
            is_internal_feed=self.is_internal_feed
        )


class SubscriptionSynchronizer:
    """
    Synchronizes data from multiple subscriptions to create time-aligned slices.
    """
    
    def __init__(self):
        self._data_buffers: Dict[str, List[BaseData]] = {}
        self._last_sync_time: Optional[datetime] = None
        self._sync_tolerance = 1.0  # 1 second tolerance for synchronization
    
    def add_data(self, subscription_id: str, data: BaseData):
        """Add data for a specific subscription."""
        if subscription_id not in self._data_buffers:
            self._data_buffers[subscription_id] = []
        
        self._data_buffers[subscription_id].append(data)
        
        # Keep buffers from growing too large
        if len(self._data_buffers[subscription_id]) > 1000:
            # Remove oldest data
            self._data_buffers[subscription_id] = self._data_buffers[subscription_id][-500:]
    
    def get_synchronized_data(self, target_time: datetime) -> Dict[str, BaseData]:
        """Get synchronized data for all subscriptions at the target time."""
        synchronized_data = {}
        
        for subscription_id, data_buffer in self._data_buffers.items():
            # Find the best data point for this time
            best_data = self._find_best_data_for_time(data_buffer, target_time)
            if best_data:
                synchronized_data[subscription_id] = best_data
        
        self._last_sync_time = target_time
        return synchronized_data
    
    def _find_best_data_for_time(self, data_buffer: List[BaseData], 
                                target_time: datetime) -> Optional[BaseData]:
        """Find the best data point for a specific time."""
        if not data_buffer:
            return None
        
        # Find data points within tolerance
        candidates = []
        for data in data_buffer:
            time_diff = abs((data.time - target_time).total_seconds())
            if time_diff <= self._sync_tolerance:
                candidates.append((data, time_diff))
        
        if not candidates:
            return None
        
        # Return the data point with the smallest time difference
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]
    
    def cleanup_old_data(self, cutoff_time: datetime):
        """Remove data older than the cutoff time."""
        for subscription_id in list(self._data_buffers.keys()):
            data_buffer = self._data_buffers[subscription_id]
            
            # Filter out old data
            filtered_data = [data for data in data_buffer if data.time >= cutoff_time]
            
            if filtered_data:
                self._data_buffers[subscription_id] = filtered_data
            else:
                # Remove empty buffers
                del self._data_buffers[subscription_id]
    
    def get_buffer_sizes(self) -> Dict[str, int]:
        """Get the size of each data buffer."""
        return {sid: len(buffer) for sid, buffer in self._data_buffers.items()}
    
    def clear(self):
        """Clear all data buffers."""
        self._data_buffers.clear()
        self._last_sync_time = None