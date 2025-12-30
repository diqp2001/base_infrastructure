from __future__ import annotations
import math
from typing import Optional, List, Dict, Union

from src.domain.entities.factor.finance.financial_assets.derivatives.structured_notes.call_spread.call_spread_factor import CallSpreadFactor


class CallSpreadVegaFactor(CallSpreadFactor):
    """
    Vega factor for call spread strategies that aggregates vega (volatility sensitivity) across multiple option legs.
    """

    def __init__(
        self,
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name="Call Spread Vega",
            group="Structured Note Greek", 
            subgroup="Vega",
            data_type="float",
            source="model",
            definition="Aggregated vega (volatility sensitivity) for call spread strategy across all option legs.",
            factor_id=factor_id,
            **kwargs,
        )

    def calculate_call_spread_vega(
        self,
        option_legs: List[Dict[str, Union[float, str, int]]],
        aggregate_method: str = "sum"
    ) -> Optional[float]:
        """
        Calculate aggregated vega for a call spread strategy.
        
        Args:
            option_legs: List of option leg parameters
            aggregate_method: Method to aggregate vegas ("sum", "weighted_sum")
            
        Returns:
            Aggregated vega value or None if calculation fails
        """
        if not option_legs:
            return None
            
        total_vega = 0.0
        total_weight = 0.0
        
        for leg in option_legs:
            try:
                # Extract leg parameters
                S = leg.get('S', 0.0)
                K = leg.get('K', 0.0) 
                r = leg.get('r', 0.0)
                sigma = leg.get('sigma', 0.0)
                T = leg.get('T', 0.0)
                position = leg.get('position', 'LONG')
                quantity = leg.get('quantity', 1)
                
                # Calculate individual option vega
                leg_vega = self._calculate_single_option_vega(S, K, r, sigma, T)
                
                if leg_vega is None:
                    continue
                    
                # Apply position and quantity
                position_multiplier = 1 if position.upper() == 'LONG' else -1
                weighted_vega = leg_vega * position_multiplier * quantity
                
                if aggregate_method == "sum":
                    total_vega += weighted_vega
                elif aggregate_method == "weighted_sum":
                    total_vega += weighted_vega * abs(quantity)
                    total_weight += abs(quantity)
                    
            except (KeyError, ValueError, TypeError):
                continue
                
        if aggregate_method == "weighted_sum" and total_weight > 0:
            return total_vega / total_weight
        else:
            return total_vega if total_vega != 0 else None

    def _calculate_single_option_vega(
        self,
        S: float,        # underlying price
        K: float,        # strike
        r: float,        # interest rate
        sigma: float,    # volatility
        T: float,        # time to maturity in years
    ) -> Optional[float]:
        """Calculate vega for a single option using Black-Scholes model."""
        
        # Validate inputs
        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return None
            
        d1, d2 = self._d1_d2(S, K, r, sigma, T)
        if d1 is None:
            return None

        # Vega is the same for calls and puts
        sqrt_T = math.sqrt(T)
        return S * self._norm_pdf(d1) * sqrt_T / 100  # Divide by 100 for 1% vol change