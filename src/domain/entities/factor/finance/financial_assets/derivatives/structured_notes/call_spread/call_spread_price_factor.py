from __future__ import annotations
import math
from typing import Optional, List, Dict, Union

from src.domain.entities.factor.finance.financial_assets.derivatives.structured_notes.call_spread.call_spread_factor import CallSpreadFactor


class CallSpreadPriceFactor(CallSpreadFactor):
    """
    Price factor for call spread strategies that aggregates pricing across multiple option legs.
    """

    def __init__(
        self,
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name="Call Spread Price",
            group="Structured Note Pricing", 
            subgroup="Price",
            data_type="float",
            source="model",
            definition="Aggregated price for call spread strategy across all option legs.",
            factor_id=factor_id,
            **kwargs,
        )

    def calculate_call_spread_price(
        self,
        option_legs: List[Dict[str, Union[float, str, int]]],
    ) -> Optional[float]:
        """
        Calculate total price for a call spread strategy.
        
        Args:
            option_legs: List of option leg parameters
            
        Returns:
            Total strategy price or None if calculation fails
        """
        if not option_legs:
            return None
            
        total_price = 0.0
        
        for leg in option_legs:
            try:
                # Extract leg parameters
                S = leg.get('S', 0.0)
                K = leg.get('K', 0.0) 
                r = leg.get('r', 0.0)
                sigma = leg.get('sigma', 0.0)
                T = leg.get('T', 0.0)
                option_type = leg.get('option_type', 'call')
                position = leg.get('position', 'LONG')
                quantity = leg.get('quantity', 1)
                
                # Calculate individual option price
                leg_price = self._calculate_single_option_price(S, K, r, sigma, T, option_type)
                
                if leg_price is None:
                    continue
                    
                # Apply position and quantity
                position_multiplier = 1 if position.upper() == 'LONG' else -1
                weighted_price = leg_price * position_multiplier * quantity
                
                total_price += weighted_price
                    
            except (KeyError, ValueError, TypeError):
                continue
                
        return total_price if total_price != 0 else None

    def _calculate_single_option_price(
        self,
        S: float,        # underlying price
        K: float,        # strike
        r: float,        # interest rate
        sigma: float,    # volatility
        T: float,        # time to maturity in years
        option_type: str = "call",
    ) -> Optional[float]:
        """Calculate price for a single option using Black-Scholes model."""
        
        # Validate inputs
        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return None
            
        d1, d2 = self._d1_d2(S, K, r, sigma, T)
        if d1 is None:
            return None

        discount_factor = math.exp(-r * T)
        
        if option_type.lower() == "call":
            return S * self._norm_cdf(d1) - K * discount_factor * self._norm_cdf(d2)
        else:  # put
            return K * discount_factor * self._norm_cdf(-d2) - S * self._norm_cdf(-d1)