"""
Call Spread Pricing Engine for SPX Market Making

This module implements pricing models for SPX call spreads using Black-Scholes
and other option pricing methodologies.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from scipy.stats import norm
from scipy.optimize import minimize_scalar

logger = logging.getLogger(__name__)


class CallSpreadPricingEngine:
    """
    Pricing engine for SPX call spreads.
    Implements various option pricing models and spread calculations.
    """
    
    def __init__(self):
        """Initialize the pricing engine."""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def black_scholes_call(
        self,
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        q: float = 0.0
    ) -> Dict[str, float]:
        """
        Calculate Black-Scholes call option price and Greeks.
        
        Args:
            S: Current underlying price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility (annualized)
            q: Dividend yield
            
        Returns:
            Dict containing price and Greeks
        """
        try:
            if T <= 0:
                # Handle expiration case
                intrinsic = max(0, S - K)
                return {
                    'price': intrinsic,
                    'delta': 1.0 if S > K else 0.0,
                    'gamma': 0.0,
                    'theta': 0.0,
                    'vega': 0.0,
                    'rho': 0.0,
                }
            
            # Black-Scholes formula with dividend yield
            d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            
            # Calculate price
            price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
            
            # Calculate Greeks
            delta = np.exp(-q * T) * norm.cdf(d1)
            gamma = np.exp(-q * T) * norm.pdf(d1) / (S * sigma * np.sqrt(T))
            theta = (-S * np.exp(-q * T) * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                    - r * K * np.exp(-r * T) * norm.cdf(d2)
                    + q * S * np.exp(-q * T) * norm.cdf(d1)) / 365
            vega = S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T) / 100
            rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
            
            return {
                'price': price,
                'delta': delta,
                'gamma': gamma,
                'theta': theta,
                'vega': vega,
                'rho': rho,
            }
            
        except Exception as e:
            self.logger.error(f"Error in Black-Scholes calculation: {e}")
            return {
                'price': 0.0,
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0,
                'rho': 0.0,
            }
    
    def price_call_spread(
        self,
        S: float,
        K_long: float,
        K_short: float,
        T: float,
        r: float,
        sigma: float,
        q: float = 0.0,
        spread_type: str = 'bull'
    ) -> Dict[str, Any]:
        """
        Price a call spread (bull or bear).
        
        Args:
            S: Current underlying price
            K_long: Strike of long call
            K_short: Strike of short call
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility (annualized)
            q: Dividend yield
            spread_type: 'bull' or 'bear'
            
        Returns:
            Dict containing spread pricing information
        """
        try:
            # Calculate individual option prices and Greeks
            long_call = self.black_scholes_call(S, K_long, T, r, sigma, q)
            short_call = self.black_scholes_call(S, K_short, T, r, sigma, q)
            
            if spread_type == 'bull':
                # Bull call spread: long lower strike, short higher strike
                net_price = long_call['price'] - short_call['price']
                net_delta = long_call['delta'] - short_call['delta']
                net_gamma = long_call['gamma'] - short_call['gamma']
                net_theta = long_call['theta'] - short_call['theta']
                net_vega = long_call['vega'] - short_call['vega']
                net_rho = long_call['rho'] - short_call['rho']
                
                max_profit = K_short - K_long - net_price
                max_loss = net_price
                breakeven = K_long + net_price
                
            else:  # bear spread
                # Bear call spread: short lower strike, long higher strike
                net_price = short_call['price'] - long_call['price']  # Credit received
                net_delta = short_call['delta'] - long_call['delta']
                net_gamma = short_call['gamma'] - long_call['gamma']
                net_theta = short_call['theta'] - long_call['theta']
                net_vega = short_call['vega'] - long_call['vega']
                net_rho = short_call['rho'] - long_call['rho']
                
                max_profit = net_price
                max_loss = K_short - K_long - net_price
                breakeven = K_long + net_price
            
            # Calculate probability of profit
            prob_profit = self._calculate_probability_of_profit(
                S, breakeven, T, r, sigma, q, spread_type
            )
            
            return {
                'spread_type': spread_type,
                'strikes': {'long': K_long, 'short': K_short},
                'net_price': net_price,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'breakeven': breakeven,
                'profit_loss_ratio': max_profit / max_loss if max_loss != 0 else float('inf'),
                'probability_of_profit': prob_profit,
                'greeks': {
                    'delta': net_delta,
                    'gamma': net_gamma,
                    'theta': net_theta,
                    'vega': net_vega,
                    'rho': net_rho,
                },
                'individual_options': {
                    'long_call': long_call,
                    'short_call': short_call,
                },
                'width': abs(K_short - K_long),
                'time_to_expiration': T,
            }
            
        except Exception as e:
            self.logger.error(f"Error pricing call spread: {e}")
            return {
                'error': str(e),
                'spread_type': spread_type,
                'strikes': {'long': K_long, 'short': K_short},
            }
    
    def find_optimal_spread_strikes(
        self,
        S: float,
        T: float,
        r: float,
        sigma: float,
        q: float = 0.0,
        target_delta: float = 0.3,
        max_width: float = 50,
        spread_type: str = 'bull'
    ) -> Dict[str, Any]:
        """
        Find optimal strike prices for a call spread based on target delta.
        
        Args:
            S: Current underlying price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility (annualized)
            q: Dividend yield
            target_delta: Target delta for the spread
            max_width: Maximum spread width
            spread_type: 'bull' or 'bear'
            
        Returns:
            Dict containing optimal strike information
        """
        try:
            if spread_type == 'bull':
                # For bull spread, find ATM strike and then optimize
                atm_strike = S
                
                # Search for optimal long strike (around target delta)
                def delta_error(k_long):
                    call_data = self.black_scholes_call(S, k_long, T, r, sigma, q)
                    return abs(call_data['delta'] - target_delta)
                
                result = minimize_scalar(
                    delta_error,
                    bounds=(S * 0.8, S * 1.2),
                    method='bounded'
                )
                
                k_long = result.x
                k_short = min(k_long + max_width, S * 1.3)
                
            else:  # bear spread
                # For bear spread, short the lower strike
                atm_strike = S
                k_long = min(S * 1.2, S + max_width)
                
                # Find optimal short strike
                def delta_error(k_short):
                    short_call = self.black_scholes_call(S, k_short, T, r, sigma, q)
                    long_call = self.black_scholes_call(S, k_long, T, r, sigma, q)
                    net_delta = short_call['delta'] - long_call['delta']
                    return abs(net_delta - target_delta)
                
                result = minimize_scalar(
                    delta_error,
                    bounds=(S * 0.8, k_long - 1),
                    method='bounded'
                )
                
                k_short = result.x
            
            # Price the optimized spread
            spread_data = self.price_call_spread(
                S, k_long, k_short, T, r, sigma, q, spread_type
            )
            
            return {
                'success': True,
                'optimal_strikes': {
                    'long': k_long,
                    'short': k_short,
                },
                'spread_data': spread_data,
                'target_delta': target_delta,
                'actual_delta': spread_data.get('greeks', {}).get('delta', 0),
            }
            
        except Exception as e:
            self.logger.error(f"Error finding optimal spread strikes: {e}")
            return {
                'success': False,
                'error': str(e),
                'target_delta': target_delta,
            }
    
    def _calculate_probability_of_profit(
        self,
        S: float,
        breakeven: float,
        T: float,
        r: float,
        sigma: float,
        q: float,
        spread_type: str
    ) -> float:
        """
        Calculate probability that the spread will be profitable at expiration.
        
        Args:
            S: Current underlying price
            breakeven: Breakeven price
            T: Time to expiration
            r: Risk-free rate
            sigma: Volatility
            q: Dividend yield
            spread_type: 'bull' or 'bear'
            
        Returns:
            Probability of profit (0-1)
        """
        try:
            # Use log-normal distribution to calculate probability
            mu = (r - q - 0.5 * sigma**2) * T
            std = sigma * np.sqrt(T)
            
            ln_S = np.log(S)
            ln_breakeven = np.log(breakeven)
            
            if spread_type == 'bull':
                # Bull spread profits if S_T > breakeven
                z = (ln_breakeven - ln_S - mu) / std
                prob = 1 - norm.cdf(z)
            else:
                # Bear spread profits if S_T < breakeven
                z = (ln_breakeven - ln_S - mu) / std
                prob = norm.cdf(z)
            
            return max(0, min(1, prob))
            
        except Exception as e:
            self.logger.error(f"Error calculating probability of profit: {e}")
            return 0.5  # Default to 50% if calculation fails
    
    def calculate_implied_volatility(
        self,
        option_price: float,
        S: float,
        K: float,
        T: float,
        r: float,
        q: float = 0.0,
        option_type: str = 'call'
    ) -> float:
        """
        Calculate implied volatility using Newton-Raphson method.
        
        Args:
            option_price: Market price of option
            S: Current underlying price
            K: Strike price
            T: Time to expiration
            r: Risk-free rate
            q: Dividend yield
            option_type: 'call' or 'put'
            
        Returns:
            Implied volatility
        """
        try:
            # Initial guess
            sigma = 0.2
            
            for i in range(100):  # Max iterations
                if option_type == 'call':
                    bs_result = self.black_scholes_call(S, K, T, r, sigma, q)
                    price = bs_result['price']
                    vega = bs_result['vega'] * 100  # Convert from percentage
                else:
                    # For put, use put-call parity
                    call_result = self.black_scholes_call(S, K, T, r, sigma, q)
                    price = call_result['price'] - S * np.exp(-q * T) + K * np.exp(-r * T)
                    vega = call_result['vega'] * 100
                
                price_diff = price - option_price
                
                if abs(price_diff) < 0.001:  # Convergence
                    break
                
                if vega == 0:
                    break
                
                # Newton-Raphson update
                sigma = sigma - price_diff / vega
                
                # Keep sigma within reasonable bounds
                sigma = max(0.001, min(5.0, sigma))
            
            return sigma
            
        except Exception as e:
            self.logger.error(f"Error calculating implied volatility: {e}")
            return 0.2  # Default volatility if calculation fails