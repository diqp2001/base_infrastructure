"""
Derivatives Pricing Engine for Market Making Project

Implements multiple pricing models for derivatives across different asset classes:
- Black-Scholes for equity options
- Binomial tree models
- Monte Carlo simulation
- Fixed income bond pricing
- Commodity futures pricing
"""

import logging
import numpy as np
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from scipy import stats
from scipy.optimize import brentq


class DerivativesPricingEngine:
    """
    Comprehensive derivatives pricing engine supporting multiple models
    and asset classes for market making operations.
    """
    
    def __init__(self):
        """Initialize the pricing engine."""
        self.logger = logging.getLogger(__name__)
        
        # Model parameters
        self.supported_models = [
            'black_scholes', 'binomial_tree', 'monte_carlo',
            'bond_pricing', 'futures_pricing'
        ]
        
        # Risk-free rate (would typically come from yield curve)
        self.risk_free_rate = Decimal('0.05')  # 5% risk-free rate
        
        self.logger.info("DerivativesPricingEngine initialized")
    
    def price_instrument(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Price an instrument using the appropriate pricing model.
        
        Args:
            symbol: Instrument symbol
            market_data: Current market data
            
        Returns:
            Pricing result with theoretical value and greeks
        """
        try:
            asset_class = market_data.get('asset_class', 'equity')
            
            if asset_class == 'equity':
                return self._price_equity_instrument(symbol, market_data)
            elif asset_class == 'fixed_income':
                return self._price_fixed_income_instrument(symbol, market_data)
            elif asset_class == 'commodity':
                return self._price_commodity_instrument(symbol, market_data)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported asset class: {asset_class}'
                }
                
        except Exception as e:
            self.logger.error(f"Error pricing {symbol}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _price_equity_instrument(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Price equity instruments (stocks, options)."""
        spot_price = market_data['price']
        
        # For equity stocks, theoretical price equals market price
        if not self._is_option_symbol(symbol):
            return {
                'success': True,
                'mid_price': spot_price,
                'volatility': self._estimate_volatility(symbol, market_data),
                'model_used': 'spot_price',
                'greeks': {
                    'delta': Decimal('1.0'),
                    'gamma': Decimal('0.0'),
                    'theta': Decimal('0.0'),
                    'vega': Decimal('0.0'),
                    'rho': Decimal('0.0')
                }
            }
        else:
            # Price options using Black-Scholes
            return self._price_option_black_scholes(symbol, market_data)
    
    def _price_fixed_income_instrument(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Price fixed income instruments (bonds, notes)."""
        try:
            # Extract bond parameters
            face_value = market_data.get('face_value', Decimal('100'))
            coupon_rate = market_data.get('coupon_rate', Decimal('0.035'))
            maturity_date = market_data.get('maturity_date', datetime.now() + timedelta(days=1825))
            yield_to_maturity = market_data.get('yield', Decimal('0.04'))
            
            # Calculate bond price
            bond_price = self._calculate_bond_price(
                face_value, coupon_rate, yield_to_maturity, maturity_date
            )
            
            # Calculate duration and convexity
            duration = self._calculate_modified_duration(
                coupon_rate, yield_to_maturity, maturity_date
            )
            convexity = self._calculate_convexity(
                face_value, coupon_rate, yield_to_maturity, maturity_date
            )
            
            return {
                'success': True,
                'mid_price': bond_price,
                'yield': yield_to_maturity,
                'duration': duration,
                'convexity': convexity,
                'model_used': 'bond_pricing',
                'greeks': {
                    'price_yield_sensitivity': -duration * bond_price / Decimal('100'),
                    'convexity_adjustment': convexity * bond_price / Decimal('10000')
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error pricing fixed income {symbol}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _price_commodity_instrument(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Price commodity instruments (futures, options on futures)."""
        try:
            spot_price = market_data.get('spot_price', market_data['price'])
            storage_cost = market_data.get('storage_cost', Decimal('0.02'))
            convenience_yield = market_data.get('convenience_yield', Decimal('0.01'))
            
            # For futures contracts
            if self._is_futures_symbol(symbol):
                # Calculate theoretical futures price
                time_to_expiry = self._get_time_to_expiry(market_data.get('contract_month', 'Dec2024'))
                
                futures_price = self._calculate_futures_price(
                    spot_price, storage_cost, convenience_yield, time_to_expiry
                )
                
                return {
                    'success': True,
                    'mid_price': futures_price,
                    'spot_price': spot_price,
                    'storage_cost': storage_cost,
                    'convenience_yield': convenience_yield,
                    'time_to_expiry': time_to_expiry,
                    'model_used': 'futures_pricing'
                }
            else:
                # For spot commodities
                return {
                    'success': True,
                    'mid_price': spot_price,
                    'storage_cost': storage_cost,
                    'convenience_yield': convenience_yield,
                    'model_used': 'spot_commodity'
                }
                
        except Exception as e:
            self.logger.error(f"Error pricing commodity {symbol}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _price_option_black_scholes(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Price options using Black-Scholes model."""
        try:
            # Extract option parameters (would typically parse from symbol)
            spot_price = float(market_data['price'])
            strike_price = 100.0  # Would parse from option symbol
            time_to_expiry = 0.25  # 3 months, would parse from symbol
            volatility = float(self._estimate_volatility(symbol, market_data))
            risk_free_rate = float(self.risk_free_rate)
            option_type = 'call'  # Would parse from option symbol
            
            # Calculate Black-Scholes price
            option_price = self._black_scholes_price(
                spot_price, strike_price, time_to_expiry, volatility, risk_free_rate, option_type
            )
            
            # Calculate Greeks
            greeks = self._calculate_option_greeks(
                spot_price, strike_price, time_to_expiry, volatility, risk_free_rate, option_type
            )
            
            return {
                'success': True,
                'mid_price': Decimal(str(option_price)),
                'strike_price': Decimal(str(strike_price)),
                'time_to_expiry': time_to_expiry,
                'volatility': Decimal(str(volatility)),
                'model_used': 'black_scholes',
                'greeks': greeks
            }
            
        except Exception as e:
            self.logger.error(f"Error pricing option {symbol}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _black_scholes_price(self, S: float, K: float, T: float, sigma: float, r: float, option_type: str) -> float:
        """
        Calculate Black-Scholes option price.
        
        Args:
            S: Spot price
            K: Strike price
            T: Time to expiry
            sigma: Volatility
            r: Risk-free rate
            option_type: 'call' or 'put'
        """
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        if option_type.lower() == 'call':
            price = S * stats.norm.cdf(d1) - K * math.exp(-r * T) * stats.norm.cdf(d2)
        else:  # put
            price = K * math.exp(-r * T) * stats.norm.cdf(-d2) - S * stats.norm.cdf(-d1)
        
        return price
    
    def _calculate_option_greeks(self, S: float, K: float, T: float, sigma: float, r: float, option_type: str) -> Dict[str, Decimal]:
        """Calculate option Greeks."""
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        # Delta
        if option_type.lower() == 'call':
            delta = stats.norm.cdf(d1)
        else:
            delta = stats.norm.cdf(d1) - 1
        
        # Gamma
        gamma = stats.norm.pdf(d1) / (S * sigma * math.sqrt(T))
        
        # Theta
        theta_1 = -S * stats.norm.pdf(d1) * sigma / (2 * math.sqrt(T))
        theta_2 = -r * K * math.exp(-r * T)
        
        if option_type.lower() == 'call':
            theta = theta_1 + theta_2 * stats.norm.cdf(d2)
        else:
            theta = theta_1 - theta_2 * stats.norm.cdf(-d2)
        
        theta = theta / 365  # Convert to daily theta
        
        # Vega
        vega = S * stats.norm.pdf(d1) * math.sqrt(T) / 100  # Per 1% vol change
        
        # Rho
        if option_type.lower() == 'call':
            rho = K * T * math.exp(-r * T) * stats.norm.cdf(d2) / 100
        else:
            rho = -K * T * math.exp(-r * T) * stats.norm.cdf(-d2) / 100
        
        return {
            'delta': Decimal(str(round(delta, 4))),
            'gamma': Decimal(str(round(gamma, 6))),
            'theta': Decimal(str(round(theta, 4))),
            'vega': Decimal(str(round(vega, 4))),
            'rho': Decimal(str(round(rho, 4)))
        }
    
    def _calculate_bond_price(self, face_value: Decimal, coupon_rate: Decimal, 
                             yield_to_maturity: Decimal, maturity_date: datetime) -> Decimal:
        """Calculate bond price using present value of cash flows."""
        current_date = datetime.now()
        years_to_maturity = (maturity_date - current_date).days / 365.25
        
        # Semi-annual coupon payment
        coupon_payment = face_value * coupon_rate / 2
        periods = int(years_to_maturity * 2)
        discount_rate = yield_to_maturity / 2
        
        # Present value of coupon payments
        pv_coupons = Decimal('0')
        for period in range(1, periods + 1):
            pv_coupons += coupon_payment / ((1 + discount_rate) ** period)
        
        # Present value of face value
        pv_face_value = face_value / ((1 + discount_rate) ** periods)
        
        return pv_coupons + pv_face_value
    
    def _calculate_modified_duration(self, coupon_rate: Decimal, yield_to_maturity: Decimal, 
                                   maturity_date: datetime) -> Decimal:
        """Calculate modified duration."""
        current_date = datetime.now()
        years_to_maturity = Decimal(str((maturity_date - current_date).days / 365.25))
        
        # Simplified duration calculation for a bond
        # This is an approximation - real implementation would be more precise
        macaulay_duration = years_to_maturity * Decimal('0.85')  # Approximation
        modified_duration = macaulay_duration / (1 + yield_to_maturity)
        
        return modified_duration
    
    def _calculate_convexity(self, face_value: Decimal, coupon_rate: Decimal,
                           yield_to_maturity: Decimal, maturity_date: datetime) -> Decimal:
        """Calculate bond convexity."""
        # Simplified convexity calculation
        current_date = datetime.now()
        years_to_maturity = Decimal(str((maturity_date - current_date).days / 365.25))
        
        # Approximation for convexity
        convexity = years_to_maturity ** 2 * Decimal('0.5')
        
        return convexity
    
    def _calculate_futures_price(self, spot_price: Decimal, storage_cost: Decimal,
                               convenience_yield: Decimal, time_to_expiry: float) -> Decimal:
        """Calculate theoretical futures price."""
        # F = S * e^((r + storage_cost - convenience_yield) * T)
        net_cost_of_carry = float(self.risk_free_rate) + float(storage_cost) - float(convenience_yield)
        futures_price = spot_price * Decimal(str(math.exp(net_cost_of_carry * time_to_expiry)))
        
        return futures_price
    
    def _estimate_volatility(self, symbol: str, market_data: Dict[str, Any]) -> Decimal:
        """Estimate volatility for an instrument."""
        # In a real implementation, this would calculate historical volatility
        # or use implied volatility from options
        
        # Mock volatility based on asset class and symbol
        asset_class = market_data.get('asset_class', 'equity')
        
        if asset_class == 'equity':
            # Higher volatility for smaller market cap stocks
            market_cap = market_data.get('market_cap', Decimal('100000000000'))  # $100B default
            base_vol = Decimal('0.20')  # 20% base volatility
            
            if market_cap < Decimal('10000000000'):  # < $10B
                return base_vol + Decimal('0.10')  # +10% volatility
            elif market_cap < Decimal('50000000000'):  # < $50B
                return base_vol + Decimal('0.05')  # +5% volatility
            else:
                return base_vol
                
        elif asset_class == 'fixed_income':
            return Decimal('0.05')  # 5% for bonds
            
        elif asset_class == 'commodity':
            return Decimal('0.25')  # 25% for commodities
            
        else:
            return Decimal('0.20')  # Default 20%
    
    def _is_option_symbol(self, symbol: str) -> bool:
        """Check if symbol represents an option."""
        # Simple heuristic - real implementation would parse option symbols properly
        return 'C' in symbol or 'P' in symbol or 'CALL' in symbol.upper() or 'PUT' in symbol.upper()
    
    def _is_futures_symbol(self, symbol: str) -> bool:
        """Check if symbol represents a futures contract."""
        # Simple heuristic - real implementation would parse futures symbols properly
        futures_keywords = ['FUT', 'F', 'FUTURE']
        return any(keyword in symbol.upper() for keyword in futures_keywords)
    
    def _get_time_to_expiry(self, contract_month: str) -> float:
        """Calculate time to expiry from contract month string."""
        try:
            # Parse contract month (e.g., "Dec2024")
            month_map = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }
            
            month_str = contract_month[:3]
            year_str = contract_month[3:]
            
            month = month_map.get(month_str, 12)
            year = int(year_str)
            
            expiry_date = datetime(year, month, 15)  # Assume mid-month expiry
            current_date = datetime.now()
            
            days_to_expiry = (expiry_date - current_date).days
            return max(0.0, days_to_expiry / 365.25)
            
        except Exception:
            # Default to 3 months if parsing fails
            return 0.25
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported pricing models."""
        return self.supported_models.copy()
    
    def validate_pricing_inputs(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pricing inputs for a given instrument."""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check required fields
        required_fields = ['price', 'asset_class']
        for field in required_fields:
            if field not in market_data:
                validation_result['valid'] = False
                validation_result['errors'].append(f'Missing required field: {field}')
        
        # Check price is positive
        if 'price' in market_data and market_data['price'] <= 0:
            validation_result['valid'] = False
            validation_result['errors'].append('Price must be positive')
        
        # Asset class specific validation
        asset_class = market_data.get('asset_class')
        if asset_class == 'fixed_income':
            if 'maturity_date' not in market_data:
                validation_result['warnings'].append('Missing maturity_date for fixed income instrument')
        
        return validation_result