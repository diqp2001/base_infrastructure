"""
Validators for Market Making Project

Provides validation functions for market making operations including:
- Data validation
- Configuration validation
- Risk limit validation
- Input sanitization
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from decimal import Decimal, InvalidOperation
import pandas as pd


class MarketMakingValidators:
    """
    Comprehensive validation utilities for market making operations.
    """
    
    def __init__(self):
        """Initialize the validators."""
        self.logger = logging.getLogger(__name__)
        
        # Validation parameters
        self.min_price = Decimal('0.01')  # Minimum valid price
        self.max_price = Decimal('1000000')  # Maximum valid price
        self.min_spread_bps = 1  # Minimum spread in basis points
        self.max_spread_bps = 1000  # Maximum spread in basis points
        self.valid_asset_classes = {'equity', 'fixed_income', 'commodity', 'forex', 'crypto'}
        self.valid_sides = {'BUY', 'SELL', 'buy', 'sell'}
        
        self.logger.info("MarketMakingValidators initialized")
    
    def validate_market_data(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate market data structure and values.
        
        Args:
            symbol: Instrument symbol
            market_data: Market data dictionary to validate
            
        Returns:
            Validation result with errors and warnings
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'symbol': symbol
        }
        
        try:
            # Check required fields
            required_fields = ['price', 'timestamp']
            for field in required_fields:
                if field not in market_data:
                    result['errors'].append(f"Missing required field: {field}")
                    result['valid'] = False
            
            # Validate price
            if 'price' in market_data:
                price_validation = self._validate_price(market_data['price'])
                if not price_validation['valid']:
                    result['errors'].extend(price_validation['errors'])
                    result['valid'] = False
                result['warnings'].extend(price_validation.get('warnings', []))
            
            # Validate bid/ask if present
            if 'bid_price' in market_data and 'ask_price' in market_data:
                spread_validation = self._validate_bid_ask_spread(
                    market_data['bid_price'], market_data['ask_price']
                )
                if not spread_validation['valid']:
                    result['errors'].extend(spread_validation['errors'])
                    result['valid'] = False
                result['warnings'].extend(spread_validation.get('warnings', []))
            
            # Validate volume
            if 'volume' in market_data:
                volume_validation = self._validate_volume(market_data['volume'])
                if not volume_validation['valid']:
                    result['errors'].extend(volume_validation['errors'])
                    result['valid'] = False
                result['warnings'].extend(volume_validation.get('warnings', []))
            
            # Validate asset class
            if 'asset_class' in market_data:
                if market_data['asset_class'] not in self.valid_asset_classes:
                    result['warnings'].append(
                        f"Unknown asset class: {market_data['asset_class']}, "
                        f"valid options: {self.valid_asset_classes}"
                    )
            
            # Validate timestamp
            if 'timestamp' in market_data:
                timestamp_validation = self._validate_timestamp(market_data['timestamp'])
                if not timestamp_validation['valid']:
                    result['errors'].extend(timestamp_validation['errors'])
                    result['valid'] = False
                result['warnings'].extend(timestamp_validation.get('warnings', []))
            
        except Exception as e:
            result['errors'].append(f"Validation exception: {str(e)}")
            result['valid'] = False
        
        return result
    
    def validate_quote_parameters(self, symbol: str, bid_price: Union[Decimal, float], 
                                ask_price: Union[Decimal, float], bid_size: int, 
                                ask_size: int) -> Dict[str, Any]:
        """
        Validate quote parameters before placing orders.
        
        Args:
            symbol: Instrument symbol
            bid_price: Bid price
            ask_price: Ask price
            bid_size: Bid size
            ask_size: Ask size
            
        Returns:
            Validation result
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'symbol': symbol
        }
        
        try:
            # Convert to Decimal for validation
            bid_decimal = self._to_decimal(bid_price)
            ask_decimal = self._to_decimal(ask_price)
            
            if bid_decimal is None:
                result['errors'].append("Invalid bid price format")
                result['valid'] = False
            
            if ask_decimal is None:
                result['errors'].append("Invalid ask price format")
                result['valid'] = False
            
            # Validate prices if conversion successful
            if bid_decimal is not None and ask_decimal is not None:
                # Check price levels
                for price, name in [(bid_decimal, 'bid'), (ask_decimal, 'ask')]:
                    price_validation = self._validate_price(price)
                    if not price_validation['valid']:
                        result['errors'].extend([f"{name} {error}" for error in price_validation['errors']])
                        result['valid'] = False
                
                # Validate bid-ask relationship
                if bid_decimal >= ask_decimal:
                    result['errors'].append("Bid price must be less than ask price")
                    result['valid'] = False
                
                # Check spread reasonableness
                spread = ask_decimal - bid_decimal
                mid_price = (bid_decimal + ask_decimal) / 2
                spread_bps = float(spread / mid_price * 10000)
                
                if spread_bps < self.min_spread_bps:
                    result['warnings'].append(f"Very tight spread: {spread_bps:.1f} bps")
                elif spread_bps > self.max_spread_bps:
                    result['warnings'].append(f"Very wide spread: {spread_bps:.1f} bps")
            
            # Validate sizes
            for size, name in [(bid_size, 'bid_size'), (ask_size, 'ask_size')]:
                size_validation = self._validate_order_size(size)
                if not size_validation['valid']:
                    result['errors'].extend([f"{name}: {error}" for error in size_validation['errors']])
                    result['valid'] = False
                result['warnings'].extend([f"{name}: {warning}" for warning in size_validation.get('warnings', [])])
            
        except Exception as e:
            result['errors'].append(f"Quote validation exception: {str(e)}")
            result['valid'] = False
        
        return result
    
    def validate_position(self, symbol: str, quantity: Union[Decimal, float], 
                         limits: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Validate a position against risk limits.
        
        Args:
            symbol: Instrument symbol
            quantity: Position quantity
            limits: Risk limits configuration
            
        Returns:
            Validation result
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'symbol': symbol
        }
        
        try:
            # Convert quantity to Decimal
            quantity_decimal = self._to_decimal(quantity)
            if quantity_decimal is None:
                result['errors'].append("Invalid quantity format")
                result['valid'] = False
                return result
            
            # Default limits if not provided
            if limits is None:
                limits = {
                    'max_position_size': Decimal('1000000'),
                    'max_position_value': Decimal('10000000'),
                    'warning_threshold': Decimal('0.8')
                }
            
            # Check position size limits
            max_size = limits.get('max_position_size', Decimal('1000000'))
            if abs(quantity_decimal) > max_size:
                result['errors'].append(
                    f"Position size {abs(quantity_decimal)} exceeds limit {max_size}"
                )
                result['valid'] = False
            
            # Warning for large positions
            warning_threshold = limits.get('warning_threshold', Decimal('0.8'))
            if abs(quantity_decimal) > max_size * warning_threshold:
                result['warnings'].append(
                    f"Large position: {abs(quantity_decimal)} "
                    f"({float(abs(quantity_decimal) / max_size * 100):.1f}% of limit)"
                )
            
            # Additional validation based on symbol type
            symbol_validation = self._validate_symbol_format(symbol)
            if not symbol_validation['valid']:
                result['warnings'].extend(symbol_validation['errors'])
            
        except Exception as e:
            result['errors'].append(f"Position validation exception: {str(e)}")
            result['valid'] = False
        
        return result
    
    def validate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate market making configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Validation result
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Validate risk parameters
            if 'risk' in config:
                risk_config = config['risk']
                
                # Check VaR limit
                if 'max_portfolio_var' in risk_config:
                    var_limit = self._to_decimal(risk_config['max_portfolio_var'])
                    if var_limit is None or var_limit <= 0 or var_limit >= 1:
                        result['errors'].append("max_portfolio_var must be between 0 and 1")
                        result['valid'] = False
                
                # Check position limits
                if 'max_position_size' in risk_config:
                    position_limit = self._to_decimal(risk_config['max_position_size'])
                    if position_limit is None or position_limit <= 0:
                        result['errors'].append("max_position_size must be positive")
                        result['valid'] = False
            
            # Validate trading parameters
            if 'trading' in config:
                trading_config = config['trading']
                
                # Check spread parameters
                for param in ['bid_ask_spread_factor', 'default_quote_size']:
                    if param in trading_config:
                        value = trading_config[param]
                        if param == 'bid_ask_spread_factor':
                            if not (0 < float(value) < 0.1):  # 0-10%
                                result['warnings'].append(f"{param} seems unusual: {value}")
                        elif param == 'default_quote_size':
                            if not isinstance(value, int) or value <= 0:
                                result['errors'].append(f"{param} must be positive integer")
                                result['valid'] = False
            
            # Validate database configuration
            if 'database' in config:
                db_config = config['database']
                
                if 'database_url' in db_config:
                    url = db_config['database_url']
                    if not isinstance(url, str) or len(url) == 0:
                        result['errors'].append("database_url must be non-empty string")
                        result['valid'] = False
            
            # Check for required sections
            required_sections = ['supported_asset_classes']
            for section in required_sections:
                if section not in config:
                    result['warnings'].append(f"Missing configuration section: {section}")
            
        except Exception as e:
            result['errors'].append(f"Configuration validation exception: {str(e)}")
            result['valid'] = False
        
        return result
    
    def validate_historical_data(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate historical data DataFrame.
        
        Args:
            symbol: Instrument symbol
            df: Historical data DataFrame
            
        Returns:
            Validation result
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'symbol': symbol,
            'data_quality': {}
        }
        
        try:
            # Check if DataFrame is empty
            if df.empty:
                result['errors'].append("Historical data is empty")
                result['valid'] = False
                return result
            
            # Check required columns
            required_columns = ['date', 'close']
            optional_columns = ['open', 'high', 'low', 'volume']
            
            missing_required = [col for col in required_columns if col not in df.columns]
            if missing_required:
                result['errors'].append(f"Missing required columns: {missing_required}")
                result['valid'] = False
            
            missing_optional = [col for col in optional_columns if col not in df.columns]
            if missing_optional:
                result['warnings'].append(f"Missing optional columns: {missing_optional}")
            
            # Data quality checks
            if 'close' in df.columns:
                # Check for negative prices
                negative_prices = (df['close'] <= 0).sum()
                if negative_prices > 0:
                    result['errors'].append(f"Found {negative_prices} non-positive prices")
                    result['valid'] = False
                
                # Check for missing data
                missing_data = df['close'].isna().sum()
                missing_percentage = (missing_data / len(df)) * 100
                result['data_quality']['missing_data_percentage'] = missing_percentage
                
                if missing_percentage > 10:  # More than 10% missing
                    result['warnings'].append(f"High missing data: {missing_percentage:.1f}%")
                
                # Check for outliers (prices more than 5 standard deviations from mean)
                if len(df) > 1:
                    price_mean = df['close'].mean()
                    price_std = df['close'].std()
                    outliers = ((df['close'] - price_mean).abs() > 5 * price_std).sum()
                    result['data_quality']['outliers_count'] = outliers
                    
                    if outliers > 0:
                        result['warnings'].append(f"Found {outliers} potential price outliers")
            
            # Check date column
            if 'date' in df.columns:
                try:
                    # Ensure dates are properly formatted
                    if df['date'].dtype == 'object':
                        pd.to_datetime(df['date'])
                    
                    # Check for duplicates
                    duplicates = df['date'].duplicated().sum()
                    if duplicates > 0:
                        result['warnings'].append(f"Found {duplicates} duplicate dates")
                    
                    # Check date range
                    date_range = pd.to_datetime(df['date'].max()) - pd.to_datetime(df['date'].min())
                    result['data_quality']['date_range_days'] = date_range.days
                    
                except Exception as e:
                    result['errors'].append(f"Date format issue: {str(e)}")
                    result['valid'] = False
            
            # Volume checks
            if 'volume' in df.columns:
                negative_volume = (df['volume'] < 0).sum()
                if negative_volume > 0:
                    result['warnings'].append(f"Found {negative_volume} negative volume values")
                
                zero_volume = (df['volume'] == 0).sum()
                zero_volume_percentage = (zero_volume / len(df)) * 100
                result['data_quality']['zero_volume_percentage'] = zero_volume_percentage
                
                if zero_volume_percentage > 5:
                    result['warnings'].append(f"High zero volume data: {zero_volume_percentage:.1f}%")
            
            # OHLC consistency checks
            if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                # High should be >= max(open, close) and Low should be <= min(open, close)
                invalid_high = (df['high'] < df[['open', 'close']].max(axis=1)).sum()
                invalid_low = (df['low'] > df[['open', 'close']].min(axis=1)).sum()
                
                if invalid_high > 0:
                    result['warnings'].append(f"Found {invalid_high} invalid high prices")
                if invalid_low > 0:
                    result['warnings'].append(f"Found {invalid_low} invalid low prices")
            
            result['data_quality']['total_records'] = len(df)
            
        except Exception as e:
            result['errors'].append(f"Historical data validation exception: {str(e)}")
            result['valid'] = False
        
        return result
    
    def sanitize_symbol(self, symbol: str) -> str:
        """
        Sanitize and normalize instrument symbol.
        
        Args:
            symbol: Raw symbol string
            
        Returns:
            Sanitized symbol
        """
        if not isinstance(symbol, str):
            return str(symbol).upper().strip()
        
        # Remove whitespace and convert to uppercase
        sanitized = symbol.strip().upper()
        
        # Remove invalid characters (keep alphanumeric, dots, hyphens)
        sanitized = re.sub(r'[^A-Z0-9.\-]', '', sanitized)
        
        return sanitized
    
    def validate_symbol_universe(self, universe: List[str]) -> Dict[str, Any]:
        """
        Validate a universe of trading symbols.
        
        Args:
            universe: List of symbols
            
        Returns:
            Validation result with sanitized symbols
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'original_symbols': universe.copy(),
            'sanitized_symbols': [],
            'invalid_symbols': []
        }
        
        try:
            if not universe:
                result['errors'].append("Universe is empty")
                result['valid'] = False
                return result
            
            for symbol in universe:
                try:
                    sanitized = self.sanitize_symbol(symbol)
                    
                    if not sanitized:
                        result['invalid_symbols'].append(symbol)
                        result['warnings'].append(f"Empty symbol after sanitization: '{symbol}'")
                        continue
                    
                    # Basic symbol format validation
                    symbol_validation = self._validate_symbol_format(sanitized)
                    if symbol_validation['valid']:
                        result['sanitized_symbols'].append(sanitized)
                    else:
                        result['invalid_symbols'].append(symbol)
                        result['warnings'].extend([f"Symbol {symbol}: {error}" for error in symbol_validation['errors']])
                
                except Exception as e:
                    result['invalid_symbols'].append(symbol)
                    result['warnings'].append(f"Error processing symbol '{symbol}': {str(e)}")
            
            # Check for duplicates
            if len(result['sanitized_symbols']) != len(set(result['sanitized_symbols'])):
                duplicates = [symbol for symbol in result['sanitized_symbols'] 
                             if result['sanitized_symbols'].count(symbol) > 1]
                result['warnings'].append(f"Duplicate symbols found: {set(duplicates)}")
            
            if not result['sanitized_symbols']:
                result['errors'].append("No valid symbols in universe")
                result['valid'] = False
            
        except Exception as e:
            result['errors'].append(f"Universe validation exception: {str(e)}")
            result['valid'] = False
        
        return result
    
    # Private helper methods
    
    def _validate_price(self, price: Union[Decimal, float, int]) -> Dict[str, Any]:
        """Validate a price value."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        try:
            price_decimal = self._to_decimal(price)
            if price_decimal is None:
                result['errors'].append("Invalid price format")
                result['valid'] = False
                return result
            
            if price_decimal <= 0:
                result['errors'].append("Price must be positive")
                result['valid'] = False
            elif price_decimal < self.min_price:
                result['warnings'].append(f"Very low price: {price_decimal}")
            elif price_decimal > self.max_price:
                result['warnings'].append(f"Very high price: {price_decimal}")
            
        except Exception as e:
            result['errors'].append(f"Price validation error: {str(e)}")
            result['valid'] = False
        
        return result
    
    def _validate_bid_ask_spread(self, bid: Union[Decimal, float], ask: Union[Decimal, float]) -> Dict[str, Any]:
        """Validate bid-ask spread."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        try:
            bid_decimal = self._to_decimal(bid)
            ask_decimal = self._to_decimal(ask)
            
            if bid_decimal is None or ask_decimal is None:
                result['errors'].append("Invalid bid or ask price format")
                result['valid'] = False
                return result
            
            if bid_decimal >= ask_decimal:
                result['errors'].append("Bid must be less than ask")
                result['valid'] = False
            else:
                spread = ask_decimal - bid_decimal
                mid = (bid_decimal + ask_decimal) / 2
                spread_bps = float(spread / mid * 10000)
                
                if spread_bps < self.min_spread_bps:
                    result['warnings'].append(f"Tight spread: {spread_bps:.1f} bps")
                elif spread_bps > self.max_spread_bps:
                    result['warnings'].append(f"Wide spread: {spread_bps:.1f} bps")
        
        except Exception as e:
            result['errors'].append(f"Spread validation error: {str(e)}")
            result['valid'] = False
        
        return result
    
    def _validate_volume(self, volume: Union[int, float]) -> Dict[str, Any]:
        """Validate volume value."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        try:
            if not isinstance(volume, (int, float)):
                result['errors'].append("Volume must be numeric")
                result['valid'] = False
                return result
            
            if volume < 0:
                result['errors'].append("Volume cannot be negative")
                result['valid'] = False
            elif volume == 0:
                result['warnings'].append("Zero volume")
            elif volume < 1000:
                result['warnings'].append("Very low volume")
        
        except Exception as e:
            result['errors'].append(f"Volume validation error: {str(e)}")
            result['valid'] = False
        
        return result
    
    def _validate_order_size(self, size: Union[int, float]) -> Dict[str, Any]:
        """Validate order size."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        try:
            if not isinstance(size, (int, float)):
                result['errors'].append("Order size must be numeric")
                result['valid'] = False
                return result
            
            if size <= 0:
                result['errors'].append("Order size must be positive")
                result['valid'] = False
            elif size < 10:
                result['warnings'].append("Very small order size")
            elif size > 1000000:
                result['warnings'].append("Very large order size")
        
        except Exception as e:
            result['errors'].append(f"Order size validation error: {str(e)}")
            result['valid'] = False
        
        return result
    
    def _validate_timestamp(self, timestamp: Union[datetime, str]) -> Dict[str, Any]:
        """Validate timestamp."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        try:
            if isinstance(timestamp, str):
                try:
                    timestamp = pd.to_datetime(timestamp)
                except Exception:
                    result['errors'].append("Invalid timestamp format")
                    result['valid'] = False
                    return result
            elif not isinstance(timestamp, datetime):
                result['errors'].append("Timestamp must be datetime or string")
                result['valid'] = False
                return result
            
            # Check if timestamp is too far in the future or past
            now = datetime.now()
            if timestamp > now + timedelta(days=1):
                result['warnings'].append("Timestamp is in the future")
            elif timestamp < now - timedelta(days=365*5):  # 5 years ago
                result['warnings'].append("Very old timestamp")
        
        except Exception as e:
            result['errors'].append(f"Timestamp validation error: {str(e)}")
            result['valid'] = False
        
        return result
    
    def _validate_symbol_format(self, symbol: str) -> Dict[str, Any]:
        """Validate symbol format."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        try:
            if not isinstance(symbol, str):
                result['errors'].append("Symbol must be string")
                result['valid'] = False
                return result
            
            if len(symbol) == 0:
                result['errors'].append("Symbol cannot be empty")
                result['valid'] = False
            elif len(symbol) < 2:
                result['warnings'].append("Very short symbol")
            elif len(symbol) > 20:
                result['warnings'].append("Very long symbol")
            
            # Check for valid characters
            if not re.match(r'^[A-Z0-9.\-]+$', symbol):
                result['warnings'].append("Symbol contains unusual characters")
        
        except Exception as e:
            result['errors'].append(f"Symbol format validation error: {str(e)}")
            result['valid'] = False
        
        return result
    
    def _to_decimal(self, value: Union[Decimal, float, int, str]) -> Optional[Decimal]:
        """Convert value to Decimal safely."""
        try:
            if isinstance(value, Decimal):
                return value
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None