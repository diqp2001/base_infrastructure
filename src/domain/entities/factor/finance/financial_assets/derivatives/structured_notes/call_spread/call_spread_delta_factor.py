from __future__ import annotations
from typing import Optional, List, Dict, Union

from src.domain.entities.factor.finance.financial_assets.derivatives.structured_notes.call_spread.call_spread_factor import CallSpreadFactor


class CallSpreadDeltaFactor(CallSpreadFactor):
    """
    Delta factor for call spread strategies that aggregates delta across multiple option legs.
    Supports both single option factors and portfolio option factors.
    """

    def __init__(
        self,
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name="Call Spread Delta",
            group="Structured Note Greek",
            subgroup="Delta",
            data_type="float",
            source="model",
            definition="Aggregated delta for call spread strategy across all option legs.",
            factor_id=factor_id,
            **kwargs,
        )

    def calculate_call_spread_delta(
        self,
        option_legs: List[Dict[str, Union[float, str, int]]],
        aggregate_method: str = "sum"
    ) -> Optional[float]:
        """
        Calculate aggregated delta for a call spread strategy.
        
        Args:
            option_legs: List of dictionaries containing option leg parameters:
                - S: underlying price
                - K: strike price
                - r: interest rate
                - sigma: volatility
                - T: time to maturity in years
                - option_type: "call" or "put"
                - position: "LONG" or "SHORT"
                - quantity: number of contracts (default 1)
            aggregate_method: Method to aggregate deltas ("sum", "weighted_sum")
            
        Returns:
            Aggregated delta value or None if calculation fails
        """
        if not option_legs:
            return None
            
        total_delta = 0.0
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
                
                # Calculate individual option delta
                leg_delta = self._calculate_single_option_delta(
                    S, K, r, sigma, T, option_type
                )
                
                if leg_delta is None:
                    continue
                    
                # Apply position and quantity
                position_multiplier = 1 if position.upper() == 'LONG' else -1
                weighted_delta = leg_delta * position_multiplier * quantity
                
                if aggregate_method == "sum":
                    total_delta += weighted_delta
                elif aggregate_method == "weighted_sum":
                    total_delta += weighted_delta * abs(quantity)
                    total_weight += abs(quantity)
                    
            except (KeyError, ValueError, TypeError):
                continue
                
        if aggregate_method == "weighted_sum" and total_weight > 0:
            return total_delta / total_weight
        else:
            return total_delta if total_delta != 0 else None

    def _calculate_single_option_delta(
        self,
        S: float,        # underlying price
        K: float,        # strike
        r: float,        # interest rate
        sigma: float,    # volatility
        T: float,        # time to maturity in years
        option_type: str = "call",
    ) -> Optional[float]:
        """Calculate delta for a single option using Black-Scholes model."""
        
        # Validate inputs
        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return None
            
        d1, d2 = self._d1_d2(S, K, r, sigma, T)
        if d1 is None:
            return None

        if option_type.lower() == "call":
            return self._norm_cdf(d1)
        else:  # put
            return self._norm_cdf(d1) - 1

    def calculate_call_spread_delta_from_factors(
        self,
        option_factors: List[Union[object, object]],  # CompanyShareOptionDeltaFactor or PortfolioCompanyShareOptionDeltaFactor
        leg_parameters: List[Dict[str, Union[float, str, int]]]
    ) -> Optional[float]:
        """
        Calculate call spread delta using existing option delta factors.
        
        Args:
            option_factors: List of option delta factor objects
            leg_parameters: List of leg parameters for each option
            
        Returns:
            Aggregated delta value or None if calculation fails
        """
        if len(option_factors) != len(leg_parameters):
            return None
            
        total_delta = 0.0
        
        for factor, params in zip(option_factors, leg_parameters):
            try:
                # Try to call delta calculation method on the factor
                if hasattr(factor, 'calculate_delta'):
                    leg_delta = factor.calculate_delta(
                        S=params.get('S', 0.0),
                        K=params.get('K', 0.0),
                        r=params.get('r', 0.0),
                        sigma=params.get('sigma', 0.0),
                        T=params.get('T', 0.0),
                        option_type=params.get('option_type', 'call')
                    )
                    
                    if leg_delta is not None:
                        position = params.get('position', 'LONG')
                        quantity = params.get('quantity', 1)
                        position_multiplier = 1 if position.upper() == 'LONG' else -1
                        total_delta += leg_delta * position_multiplier * quantity
                        
            except (AttributeError, TypeError, ValueError):
                continue
                
        return total_delta if total_delta != 0 else None