"""
Data Validators for SPX Call Spread Market Making

This module provides validation utilities for market data, option chains,
and trading parameters to ensure data integrity.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Data validator for SPX call spread market making.
    Validates market data, option chains, and trading parameters.
    """
    
    def __init__(self):
        """Initialize the data validator."""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Validation thresholds
        self.spx_price_range = (1000, 10000)  # Reasonable SPX price range
        self.vix_range = (5, 100)             # VIX range
        self.iv_range = (0.01, 5.0)           # Implied volatility range (1%-500%)
        self.max_dte = 730                    # Maximum days to expiration (2 years)
        self.min_strike_spacing = 1           # Minimum strike spacing
        self.max_strike_spacing = 500         # Maximum strike spacing
    
    def validate_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate market data for consistency and reasonableness.
        
        Args:
            market_data: Market data dictionary
            
        Returns:
            Dict containing validation results
        """
        try:
            errors = []
            warnings = []
            
            # Validate SPX price
            spx_price = market_data.get('spx_price')
            if spx_price is None:
                errors.append("Missing SPX price")
            elif not isinstance(spx_price, (int, float)):
                errors.append("SPX price must be numeric")
            elif not (self.spx_price_range[0] <= spx_price <= self.spx_price_range[1]):
                warnings.append(f"SPX price {spx_price} outside normal range {self.spx_price_range}")
            
            # Validate VIX
            vix = market_data.get('vix')
            if vix is not None:
                if not isinstance(vix, (int, float)):
                    errors.append("VIX must be numeric")
                elif not (self.vix_range[0] <= vix <= self.vix_range[1]):
                    warnings.append(f"VIX {vix} outside normal range {self.vix_range}")
            
            # Validate timestamp
            timestamp = market_data.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp)
                    except ValueError:
                        errors.append("Invalid timestamp format")
                
                # Check if timestamp is too old or in future
                now = datetime.now()
                if isinstance(timestamp, datetime):
                    if timestamp > now + timedelta(hours=1):
                        warnings.append("Timestamp is in the future")
                    elif timestamp < now - timedelta(days=7):
                        warnings.append("Timestamp is more than 1 week old")
            
            # Validate OHLC data if present
            ohlc_validation = self._validate_ohlc_data(market_data)
            errors.extend(ohlc_validation['errors'])
            warnings.extend(ohlc_validation['warnings'])
            
            return {
                'is_valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'validation_timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error validating market data: {e}")
            return {
                'is_valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': [],
            }
    
    def validate_option_chain(self, option_chain: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate option chain data.
        
        Args:
            option_chain: Option chain data
            
        Returns:
            Dict containing validation results
        """
        try:
            errors = []
            warnings = []
            
            # Validate expiration dates
            expiries = option_chain.get('expiries', [])
            if not expiries:
                errors.append("No expiration dates provided")
            else:
                expiry_validation = self._validate_expiry_dates(expiries)
                errors.extend(expiry_validation['errors'])
                warnings.extend(expiry_validation['warnings'])
            
            # Validate strikes
            strikes = option_chain.get('strikes', [])
            if not strikes:
                errors.append("No strikes provided")
            else:
                strike_validation = self._validate_strikes(strikes)
                errors.extend(strike_validation['errors'])
                warnings.extend(strike_validation['warnings'])
            
            # Validate option data if present
            options = option_chain.get('options', [])
            if options:
                option_validation = self._validate_individual_options(options)
                errors.extend(option_validation['errors'])
                warnings.extend(option_validation['warnings'])
            
            return {
                'is_valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'expiries_count': len(expiries),
                'strikes_count': len(strikes),
                'options_count': len(options),
                'validation_timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error validating option chain: {e}")
            return {
                'is_valid': False,
                'errors': [f"Option chain validation error: {str(e)}"],
                'warnings': [],
            }
    
    def validate_spread_parameters(self, spread_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate call spread parameters.
        
        Args:
            spread_params: Spread parameter dictionary
            
        Returns:
            Dict containing validation results
        """
        try:
            errors = []
            warnings = []
            
            # Validate spread type
            spread_type = spread_params.get('spread_type')
            valid_types = ['bull_call_spread', 'bear_call_spread']
            if spread_type not in valid_types:
                errors.append(f"Invalid spread type. Must be one of: {valid_types}")
            
            # Validate strikes
            long_strike = spread_params.get('long_strike')
            short_strike = spread_params.get('short_strike')
            
            if long_strike is None or short_strike is None:
                errors.append("Both long_strike and short_strike must be provided")
            elif not all(isinstance(s, (int, float)) for s in [long_strike, short_strike]):
                errors.append("Strikes must be numeric")
            else:
                # Validate strike relationship
                if spread_type == 'bull_call_spread' and long_strike >= short_strike:
                    errors.append("Bull call spread: long strike must be less than short strike")
                elif spread_type == 'bear_call_spread' and long_strike <= short_strike:
                    errors.append("Bear call spread: long strike must be greater than short strike")
                
                # Check strike spacing
                strike_width = abs(short_strike - long_strike)
                if strike_width > 200:  # Arbitrary large width
                    warnings.append(f"Large strike width: {strike_width}")
                elif strike_width < 5:  # Very narrow spread
                    warnings.append(f"Very narrow spread width: {strike_width}")
            
            # Validate expiry
            expiry = spread_params.get('expiry')
            if expiry:
                if isinstance(expiry, str):
                    try:
                        expiry_dt = datetime.fromisoformat(expiry)
                    except ValueError:
                        errors.append("Invalid expiry date format")
                        expiry_dt = None
                else:
                    expiry_dt = expiry
                
                if expiry_dt and isinstance(expiry_dt, datetime):
                    days_to_expiry = (expiry_dt - datetime.now()).days
                    if days_to_expiry < 0:
                        errors.append("Expiry date is in the past")
                    elif days_to_expiry > self.max_dte:
                        warnings.append(f"Expiry is very far out: {days_to_expiry} days")
                    elif days_to_expiry < 1:
                        warnings.append(f"Expiry is very soon: {days_to_expiry} days")
            
            # Validate position size
            size = spread_params.get('size')
            if size is not None:
                if not isinstance(size, (int, float)) or size <= 0:
                    errors.append("Position size must be a positive number")
                elif size > 100:  # Arbitrary large size
                    warnings.append(f"Large position size: {size}")
            
            # Validate underlying price
            underlying_price = spread_params.get('underlying_price')
            if underlying_price is not None:
                if not isinstance(underlying_price, (int, float)):
                    errors.append("Underlying price must be numeric")
                elif not (self.spx_price_range[0] <= underlying_price <= self.spx_price_range[1]):
                    warnings.append(f"Underlying price outside normal range: {underlying_price}")
            
            return {
                'is_valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'validation_timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error validating spread parameters: {e}")
            return {
                'is_valid': False,
                'errors': [f"Spread validation error: {str(e)}"],
                'warnings': [],
            }
    
    def validate_portfolio_data(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate portfolio data for backtesting and risk management.
        
        Args:
            portfolio_data: Portfolio data dictionary
            
        Returns:
            Dict containing validation results
        """
        try:
            errors = []
            warnings = []
            
            # Validate portfolio value
            portfolio_value = portfolio_data.get('portfolio_value')
            if portfolio_value is None:
                errors.append("Missing portfolio value")
            elif not isinstance(portfolio_value, (int, float)):
                errors.append("Portfolio value must be numeric")
            elif portfolio_value <= 0:
                errors.append("Portfolio value must be positive")
            
            # Validate cash
            cash = portfolio_data.get('cash')
            if cash is not None:
                if not isinstance(cash, (int, float)):
                    errors.append("Cash must be numeric")
                elif cash < 0:
                    warnings.append("Negative cash position")
                
                # Check cash ratio
                if portfolio_value and portfolio_value > 0:
                    cash_ratio = cash / portfolio_value
                    if cash_ratio > 0.5:
                        warnings.append(f"High cash ratio: {cash_ratio:.1%}")
                    elif cash_ratio < 0:
                        warnings.append(f"Negative cash ratio: {cash_ratio:.1%}")
            
            # Validate positions
            positions = portfolio_data.get('positions', {})
            if positions:
                position_validation = self._validate_positions(positions)
                errors.extend(position_validation['errors'])
                warnings.extend(position_validation['warnings'])
            
            # Validate daily P&L
            daily_pnl = portfolio_data.get('daily_pnl')
            if daily_pnl is not None and portfolio_value:
                pnl_ratio = abs(daily_pnl) / portfolio_value
                if pnl_ratio > 0.1:  # More than 10% daily move
                    warnings.append(f"Large daily P&L: {daily_pnl:.2f} ({pnl_ratio:.1%})")
            
            return {
                'is_valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'positions_count': len(positions),
                'validation_timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error validating portfolio data: {e}")
            return {
                'is_valid': False,
                'errors': [f"Portfolio validation error: {str(e)}"],
                'warnings': [],
            }
    
    def _validate_ohlc_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate OHLC data if present."""
        errors = []
        warnings = []
        
        ohlc_fields = ['open', 'high', 'low', 'close']
        ohlc_values = {}
        
        # Check if OHLC fields are present and numeric
        for field in ohlc_fields:
            value = market_data.get(field)
            if value is not None:
                if not isinstance(value, (int, float)):
                    errors.append(f"{field} must be numeric")
                else:
                    ohlc_values[field] = value
        
        # Validate OHLC relationships if all present
        if len(ohlc_values) == 4:
            o, h, l, c = ohlc_values['open'], ohlc_values['high'], ohlc_values['low'], ohlc_values['close']
            
            if h < max(o, c):
                errors.append("High must be >= max(open, close)")
            if l > min(o, c):
                errors.append("Low must be <= min(open, close)")
            
            # Check for unusual spreads
            spread = h - l
            avg_price = (o + c) / 2
            if avg_price > 0 and spread / avg_price > 0.1:  # More than 10% spread
                warnings.append(f"Large intraday spread: {spread:.2f} ({spread/avg_price:.1%})")
        
        # Validate volume if present
        volume = market_data.get('volume')
        if volume is not None:
            if not isinstance(volume, (int, float)) or volume < 0:
                errors.append("Volume must be non-negative numeric")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_expiry_dates(self, expiries: List[Union[str, datetime]]) -> Dict[str, Any]:
        """Validate expiry dates."""
        errors = []
        warnings = []
        
        now = datetime.now()
        
        for i, expiry in enumerate(expiries):
            if isinstance(expiry, str):
                try:
                    expiry_dt = datetime.fromisoformat(expiry)
                except ValueError:
                    errors.append(f"Invalid expiry date format at index {i}: {expiry}")
                    continue
            else:
                expiry_dt = expiry
            
            if not isinstance(expiry_dt, datetime):
                errors.append(f"Expiry at index {i} must be datetime or ISO string")
                continue
            
            # Check if expiry is in the past
            if expiry_dt < now:
                warnings.append(f"Expiry at index {i} is in the past: {expiry_dt}")
            
            # Check if expiry is too far out
            days_to_expiry = (expiry_dt - now).days
            if days_to_expiry > self.max_dte:
                warnings.append(f"Expiry at index {i} is very far out: {days_to_expiry} days")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_strikes(self, strikes: List[Union[int, float]]) -> Dict[str, Any]:
        """Validate strike prices."""
        errors = []
        warnings = []
        
        # Check if all strikes are numeric
        numeric_strikes = []
        for i, strike in enumerate(strikes):
            if not isinstance(strike, (int, float)):
                errors.append(f"Strike at index {i} must be numeric: {strike}")
            else:
                numeric_strikes.append(strike)
        
        if not numeric_strikes:
            return {'errors': errors, 'warnings': warnings}
        
        # Sort strikes for analysis
        sorted_strikes = sorted(numeric_strikes)
        
        # Check strike spacing
        if len(sorted_strikes) > 1:
            min_spacing = min(sorted_strikes[i+1] - sorted_strikes[i] for i in range(len(sorted_strikes)-1))
            max_spacing = max(sorted_strikes[i+1] - sorted_strikes[i] for i in range(len(sorted_strikes)-1))
            
            if min_spacing < self.min_strike_spacing:
                warnings.append(f"Very small strike spacing: {min_spacing}")
            if max_spacing > self.max_strike_spacing:
                warnings.append(f"Very large strike spacing: {max_spacing}")
        
        # Check strike range
        strike_range = max(sorted_strikes) - min(sorted_strikes)
        if strike_range > 1000:  # Very wide range
            warnings.append(f"Very wide strike range: {strike_range}")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_individual_options(self, options: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate individual option data."""
        errors = []
        warnings = []
        
        for i, option in enumerate(options):
            # Validate required fields
            required_fields = ['strike', 'expiry', 'option_type']
            for field in required_fields:
                if field not in option:
                    errors.append(f"Option {i} missing required field: {field}")
            
            # Validate option type
            option_type = option.get('option_type', '').upper()
            if option_type not in ['CALL', 'PUT']:
                errors.append(f"Option {i} invalid option_type: {option_type}")
            
            # Validate implied volatility if present
            iv = option.get('implied_volatility')
            if iv is not None:
                if not isinstance(iv, (int, float)) or iv <= 0:
                    errors.append(f"Option {i} implied volatility must be positive: {iv}")
                elif not (self.iv_range[0] <= iv <= self.iv_range[1]):
                    warnings.append(f"Option {i} IV outside normal range: {iv}")
            
            # Validate bid/ask if present
            bid = option.get('bid')
            ask = option.get('ask')
            if bid is not None and ask is not None:
                if not isinstance(bid, (int, float)) or not isinstance(ask, (int, float)):
                    errors.append(f"Option {i} bid/ask must be numeric")
                elif bid < 0 or ask < 0:
                    errors.append(f"Option {i} bid/ask must be non-negative")
                elif bid > ask:
                    errors.append(f"Option {i} bid ({bid}) > ask ({ask})")
                elif ask > 0 and (ask - bid) / ask > 0.5:  # Wide spread
                    warnings.append(f"Option {i} wide bid-ask spread: {ask - bid:.2f}")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_positions(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """Validate portfolio positions."""
        errors = []
        warnings = []
        
        total_exposure = 0
        
        for pos_id, position in positions.items():
            # Validate position structure
            if not isinstance(position, dict):
                errors.append(f"Position {pos_id} must be a dictionary")
                continue
            
            # Validate position type
            pos_type = position.get('type')
            if not pos_type:
                errors.append(f"Position {pos_id} missing type")
            
            # Validate size
            size = position.get('size')
            if size is not None:
                if not isinstance(size, (int, float)) or size <= 0:
                    errors.append(f"Position {pos_id} size must be positive: {size}")
            
            # Validate strikes if present
            strikes = position.get('strikes', {})
            if strikes:
                for strike_type, strike in strikes.items():
                    if not isinstance(strike, (int, float)):
                        errors.append(f"Position {pos_id} {strike_type} strike must be numeric: {strike}")
            
            # Calculate exposure
            underlying_price = position.get('underlying_price', 4500)
            position_size = position.get('size', 1)
            exposure = underlying_price * position_size
            total_exposure += exposure
            
            # Check for very large positions
            if exposure > 100000:  # $100k exposure
                warnings.append(f"Position {pos_id} has large exposure: ${exposure:,.0f}")
        
        # Check total exposure
        if total_exposure > 1000000:  # $1M total exposure
            warnings.append(f"Total portfolio exposure is large: ${total_exposure:,.0f}")
        
        return {'errors': errors, 'warnings': warnings}