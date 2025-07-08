"""
SecurityCache class for caching security data.
"""

from typing import Optional
from decimal import Decimal
from dataclasses import dataclass, field

from ..data_types import BaseData


@dataclass
class SecurityCache:
    """
    Caches the most recent security data for fast access.
    """
    _last_data: Optional[BaseData] = field(default=None, init=False)
    _bid_price: Decimal = field(default=Decimal('0'), init=False)
    _ask_price: Decimal = field(default=Decimal('0'), init=False)
    _bid_size: int = field(default=0, init=False)
    _ask_size: int = field(default=0, init=False)
    _open_interest: int = field(default=0, init=False)
    
    @property
    def last_data(self) -> Optional[BaseData]:
        """The last data point received."""
        return self._last_data
    
    @property
    def bid_price(self) -> Decimal:
        """Current bid price."""
        return self._bid_price
    
    @property
    def ask_price(self) -> Decimal:
        """Current ask price."""
        return self._ask_price
    
    @property
    def bid_size(self) -> int:
        """Current bid size."""
        return self._bid_size
    
    @property
    def ask_size(self) -> int:
        """Current ask size."""
        return self._ask_size
    
    @property
    def open_interest(self) -> int:
        """Current open interest."""
        return self._open_interest
    
    def store_data(self, data: BaseData) -> None:
        """Store new data in the cache."""
        self._last_data = data
        
        # Update derived properties based on data type
        if hasattr(data, 'bid_price'):
            self._bid_price = data.bid_price
        if hasattr(data, 'ask_price'):
            self._ask_price = data.ask_price
        if hasattr(data, 'bid_size'):
            self._bid_size = data.bid_size
        if hasattr(data, 'ask_size'):
            self._ask_size = data.ask_size
        if hasattr(data, 'open_interest'):
            self._open_interest = data.open_interest
    
    def clear(self) -> None:
        """Clear all cached data."""
        self._last_data = None
        self._bid_price = Decimal('0')
        self._ask_price = Decimal('0')
        self._bid_size = 0
        self._ask_size = 0
        self._open_interest = 0