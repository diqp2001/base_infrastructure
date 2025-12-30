from __future__ import annotations
import math
from typing import Optional, List, Dict, Union

from src.domain.entities.factor.finance.financial_assets.derivatives.structured_notes.call_spread.call_spread_factor import CallSpreadFactor


class CallSpreadThetaFactor(CallSpreadFactor):
    """
    Theta factor for call spread strategies that aggregates theta (time decay) across multiple option legs.
    """

    def __init__(
        self,
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name="Call Spread Theta",
            group="Structured Note Greek", 
            subgroup="Theta",
            data_type="float",
            source="model",
            definition="Aggregated theta (time decay) for call spread strategy across all option legs.",
            factor_id=factor_id,
            **kwargs,
        )

    def calculate_call_spread_theta(
        self,
        option_legs: List[Dict[str, Union[float, str, int]]],
        aggregate_method: str = "sum"
    ) -> Optional[float]:
        """
        Calculate aggregated theta for a call spread strategy.
        
        Args:
            option_legs: List of option leg parameters
            aggregate_method: Method to aggregate thetas ("sum", "weighted_sum")
            
        Returns:
            Aggregated theta value or None if calculation fails
        """
        if not option_legs:
            return None
            
        total_theta = 0.0
        total_weight = 0.0
        
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
                
                # Calculate individual option theta
                leg_theta = self._calculate_single_option_theta(S, K, r, sigma, T, option_type)
                
                if leg_theta is None:
                    continue
                    
                # Apply position and quantity
                position_multiplier = 1 if position.upper() == 'LONG' else -1
                weighted_theta = leg_theta * position_multiplier * quantity
                
                if aggregate_method == "sum":
                    total_theta += weighted_theta
                elif aggregate_method == "weighted_sum":
                    total_theta += weighted_theta * abs(quantity)
                    total_weight += abs(quantity)
                    
            except (KeyError, ValueError, TypeError):
                continue
                
        if aggregate_method == "weighted_sum" and total_weight > 0:
            return total_theta / total_weight
        else:
            return total_theta if total_theta != 0 else None

    def _calculate_single_option_theta(
        self,
        S: float,        # underlying price
        K: float,        # strike
        r: float,        # interest rate
        sigma: float,    # volatility
        T: float,        # time to maturity in years
        option_type: str = "call",
    ) -> Optional[float]:
        """Calculate theta for a single option using Black-Scholes model."""
        
        # Validate inputs
        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return None
            
        d1, d2 = self._d1_d2(S, K, r, sigma, T)
        if d1 is None:
            return None

        # Common theta components
        sqrt_T = math.sqrt(T)
        theta_common = -(S * self._norm_pdf(d1) * sigma) / (2 * sqrt_T)
        
        if option_type.lower() == "call":
            theta_interest = -r * K * math.exp(-r * T) * self._norm_cdf(d2)
            return (theta_common + theta_interest) / 365  # Convert to daily theta
        else:  # put
            theta_interest = r * K * math.exp(-r * T) * self._norm_cdf(-d2)
            return (theta_common + theta_interest) / 365  # Convert to daily theta