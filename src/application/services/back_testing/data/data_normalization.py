"""
Data normalization utilities for handling splits, dividends, and adjustments.
"""

from datetime import datetime
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass

from ..common.data_types import BaseData, TradeBar, QuoteBar
from ..common.symbol import Symbol
from ..common.enums import DataNormalizationMode


@dataclass
class CorporateAction:
    """
    Represents a corporate action (split, dividend, etc.).
    """
    symbol: Symbol
    date: datetime
    action_type: str  # 'split', 'dividend', 'merger', etc.
    ratio: Decimal  # For splits (e.g., 2.0 for 2:1 split)
    amount: Decimal  # For dividends (amount per share)
    description: str = ""
    
    def __post_init__(self):
        """Post-initialization to ensure proper types."""
        if not isinstance(self.ratio, Decimal):
            self.ratio = Decimal(str(self.ratio))
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))


class DataNormalizationHelper:
    """
    Helper class for normalizing market data based on corporate actions.
    """
    
    def __init__(self):
        self._corporate_actions: Dict[Symbol, List[CorporateAction]] = {}
        self._normalization_cache: Dict[str, List[BaseData]] = {}
    
    def add_corporate_action(self, action: CorporateAction):
        """Add a corporate action."""
        symbol = action.symbol
        
        if symbol not in self._corporate_actions:
            self._corporate_actions[symbol] = []
        
        self._corporate_actions[symbol].append(action)
        
        # Sort by date (most recent first)
        self._corporate_actions[symbol].sort(key=lambda x: x.date, reverse=True)
        
        # Clear cache for this symbol
        self._clear_cache_for_symbol(symbol)
    
    def remove_corporate_actions(self, symbol: Symbol):
        """Remove all corporate actions for a symbol."""
        if symbol in self._corporate_actions:
            del self._corporate_actions[symbol]
        
        self._clear_cache_for_symbol(symbol)
    
    def normalize_data(self, data: List[BaseData], mode: DataNormalizationMode) -> List[BaseData]:
        """
        Normalize data based on the specified mode.
        """
        if not data:
            return []
        
        # Group data by symbol
        data_by_symbol: Dict[Symbol, List[BaseData]] = {}
        for data_point in data:
            symbol = data_point.symbol
            if symbol not in data_by_symbol:
                data_by_symbol[symbol] = []
            data_by_symbol[symbol].append(data_point)
        
        # Normalize each symbol's data
        normalized_data = []
        for symbol, symbol_data in data_by_symbol.items():
            normalized_symbol_data = self._normalize_symbol_data(symbol_data, mode)
            normalized_data.extend(normalized_symbol_data)
        
        # Sort by time
        normalized_data.sort(key=lambda x: x.time)
        
        return normalized_data
    
    def _normalize_symbol_data(self, data: List[BaseData], mode: DataNormalizationMode) -> List[BaseData]:
        """Normalize data for a specific symbol."""
        if not data or mode == DataNormalizationMode.RAW:
            return data
        
        symbol = data[0].symbol
        
        # Check cache
        cache_key = f"{symbol}_{mode.value}_{len(data)}"
        if cache_key in self._normalization_cache:
            return self._normalization_cache[cache_key]
        
        # Get corporate actions for this symbol
        actions = self._corporate_actions.get(symbol, [])
        if not actions:
            # No actions, return original data
            self._normalization_cache[cache_key] = data
            return data
        
        # Sort data by time (oldest first for processing)
        sorted_data = sorted(data, key=lambda x: x.time)
        normalized_data = []
        
        for data_point in sorted_data:
            normalized_point = self._normalize_data_point(data_point, actions, mode)
            normalized_data.append(normalized_point)
        
        # Cache the result
        self._normalization_cache[cache_key] = normalized_data
        
        return normalized_data
    
    def _normalize_data_point(self, data_point: BaseData, actions: List[CorporateAction], 
                            mode: DataNormalizationMode) -> BaseData:
        """Normalize a single data point."""
        
        # Find actions that occurred after this data point
        applicable_actions = [action for action in actions if action.date > data_point.time]
        
        if not applicable_actions:
            # No actions to apply
            return data_point
        
        # Apply adjustments based on mode
        if isinstance(data_point, TradeBar):
            return self._normalize_trade_bar(data_point, applicable_actions, mode)
        elif isinstance(data_point, QuoteBar):
            return self._normalize_quote_bar(data_point, applicable_actions, mode)
        else:
            return self._normalize_base_data(data_point, applicable_actions, mode)
    
    def _normalize_trade_bar(self, trade_bar: TradeBar, actions: List[CorporateAction], 
                           mode: DataNormalizationMode) -> TradeBar:
        """Normalize a trade bar."""
        
        # Calculate adjustment factors
        price_factor, volume_factor = self._calculate_adjustment_factors(actions, mode)
        
        # Create normalized trade bar
        normalized_bar = TradeBar(
            symbol=trade_bar.symbol,
            time=trade_bar.time,
            value=trade_bar.close * price_factor,
            data_type=trade_bar.data_type,
            open=trade_bar.open * price_factor,
            high=trade_bar.high * price_factor,
            low=trade_bar.low * price_factor,
            close=trade_bar.close * price_factor,
            volume=int(trade_bar.volume * volume_factor),
            period=trade_bar.period
        )
        
        return normalized_bar
    
    def _normalize_quote_bar(self, quote_bar: QuoteBar, actions: List[CorporateAction], 
                           mode: DataNormalizationMode) -> QuoteBar:
        """Normalize a quote bar."""
        
        price_factor, _ = self._calculate_adjustment_factors(actions, mode)
        
        # Normalize bid and ask if they exist
        normalized_bid = None
        if quote_bar.bid:
            from ..common.data_types import Bar
            normalized_bid = Bar(
                open=quote_bar.bid.open * price_factor,
                high=quote_bar.bid.high * price_factor,
                low=quote_bar.bid.low * price_factor,
                close=quote_bar.bid.close * price_factor
            )
        
        normalized_ask = None
        if quote_bar.ask:
            from ..common.data_types import Bar
            normalized_ask = Bar(
                open=quote_bar.ask.open * price_factor,
                high=quote_bar.ask.high * price_factor,
                low=quote_bar.ask.low * price_factor,
                close=quote_bar.ask.close * price_factor
            )
        
        normalized_quote_bar = QuoteBar(
            symbol=quote_bar.symbol,
            time=quote_bar.time,
            value=quote_bar.value * price_factor,
            data_type=quote_bar.data_type,
            bid=normalized_bid,
            ask=normalized_ask,
            last_bid_size=quote_bar.last_bid_size,
            last_ask_size=quote_bar.last_ask_size,
            period=quote_bar.period
        )
        
        return normalized_quote_bar
    
    def _normalize_base_data(self, data_point: BaseData, actions: List[CorporateAction], 
                           mode: DataNormalizationMode) -> BaseData:
        """Normalize a base data point."""
        
        price_factor, _ = self._calculate_adjustment_factors(actions, mode)
        
        # Create normalized data point
        normalized_data = data_point.clone()
        normalized_data.value = data_point.value * price_factor
        
        return normalized_data
    
    def _calculate_adjustment_factors(self, actions: List[CorporateAction], 
                                   mode: DataNormalizationMode) -> Tuple[Decimal, Decimal]:
        """
        Calculate adjustment factors for price and volume.
        Returns (price_factor, volume_factor).
        """
        price_factor = Decimal('1.0')
        volume_factor = Decimal('1.0')
        
        for action in actions:
            if action.action_type == 'split':
                if mode in [DataNormalizationMode.SPLIT_ADJUSTED, DataNormalizationMode.ADJUSTED, 
                          DataNormalizationMode.TOTAL_RETURN]:
                    # Adjust for split
                    split_ratio = action.ratio
                    price_factor /= split_ratio
                    volume_factor *= split_ratio
            
            elif action.action_type == 'dividend':
                if mode in [DataNormalizationMode.ADJUSTED, DataNormalizationMode.TOTAL_RETURN]:
                    # Adjust for dividend (subtract dividend from price)
                    # This is a simplified approach - in reality, dividend adjustments are more complex
                    dividend_adjustment = action.amount / price_factor  # Account for previous adjustments
                    price_factor *= (price_factor - dividend_adjustment) / price_factor
        
        return price_factor, volume_factor
    
    def get_corporate_actions(self, symbol: Symbol, start_date: datetime = None, 
                            end_date: datetime = None) -> List[CorporateAction]:
        """Get corporate actions for a symbol within a date range."""
        actions = self._corporate_actions.get(symbol, [])
        
        if start_date or end_date:
            filtered_actions = []
            for action in actions:
                if start_date and action.date < start_date:
                    continue
                if end_date and action.date > end_date:
                    continue
                filtered_actions.append(action)
            return filtered_actions
        
        return actions.copy()
    
    def _clear_cache_for_symbol(self, symbol: Symbol):
        """Clear normalization cache for a specific symbol."""
        keys_to_remove = [key for key in self._normalization_cache.keys() if key.startswith(str(symbol))]
        for key in keys_to_remove:
            del self._normalization_cache[key]
    
    def clear_cache(self):
        """Clear all normalization cache."""
        self._normalization_cache.clear()
    
    def get_split_adjusted_price(self, symbol: Symbol, original_price: Decimal, 
                               price_date: datetime, reference_date: datetime = None) -> Decimal:
        """
        Get split-adjusted price for a symbol.
        Adjusts original_price from price_date to reference_date (or current date).
        """
        if reference_date is None:
            reference_date = datetime.utcnow()
        
        actions = self._corporate_actions.get(symbol, [])
        
        # Find splits between price_date and reference_date
        applicable_splits = [
            action for action in actions 
            if (action.action_type == 'split' and 
                price_date <= action.date <= reference_date)
        ]
        
        adjusted_price = original_price
        for split in applicable_splits:
            adjusted_price /= split.ratio
        
        return adjusted_price
    
    def get_total_return_multiplier(self, symbol: Symbol, start_date: datetime, 
                                  end_date: datetime) -> Decimal:
        """
        Calculate total return multiplier including dividends and splits.
        This multiplier can be applied to calculate total return.
        """
        actions = self._corporate_actions.get(symbol, [])
        
        # Find actions between start and end date
        applicable_actions = [
            action for action in actions 
            if start_date <= action.date <= end_date
        ]
        
        multiplier = Decimal('1.0')
        
        for action in applicable_actions:
            if action.action_type == 'split':
                multiplier *= action.ratio
            elif action.action_type == 'dividend':
                # This is simplified - real total return calculation is more complex
                # and depends on the stock price at the time of dividend
                pass
        
        return multiplier