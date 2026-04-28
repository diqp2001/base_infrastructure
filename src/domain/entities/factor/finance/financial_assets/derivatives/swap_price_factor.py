from __future__ import annotations
import math
from typing import Optional, List
from datetime import datetime

from src.domain.entities.factor.finance.financial_assets.derivatives.swap_factor import SwapFactor


class SwapPriceFactor(SwapFactor):
    """Price factor for swap contracts, calculating present value of fixed and floating legs."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            frequency=frequency,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
            **kwargs,
        )

    def calculate(
        self,
        fixed_rate: float,
        floating_rates: List[float],
        notional: float,
        fixed_payment_periods: List[float],
        floating_payment_periods: List[float],
        discount_factors: List[float],
        swap_type: str = "pay_fixed"
    ) -> Optional[float]:
        """
        Calculate the market value of a swap as the difference between fixed and floating leg values.
        
        Parameters
        ----------
        fixed_rate : float
            Fixed rate of the swap
        floating_rates : List[float]
            Expected floating rates for each payment period
        notional : float
            Notional amount of the swap
        fixed_payment_periods : List[float]
            Time periods (in years) for fixed leg payments
        floating_payment_periods : List[float]
            Time periods (in years) for floating leg payments
        discount_factors : List[float]
            Discount factors for each payment date
        swap_type : str
            'pay_fixed' (default) or 'receive_fixed'
            
        Returns
        -------
        float | None
            Present value of the swap
        """
        
        if not all([
            fixed_payment_periods, 
            floating_payment_periods, 
            floating_rates,
            discount_factors
        ]):
            return None
            
        if len(floating_rates) != len(floating_payment_periods):
            return None
            
        if len(discount_factors) < max(len(fixed_payment_periods), len(floating_payment_periods)):
            return None

        try:
            # Calculate present value of fixed leg
            fixed_leg_pv = 0.0
            for i, period in enumerate(fixed_payment_periods):
                if i < len(discount_factors):
                    fixed_payment = notional * fixed_rate * period
                    fixed_leg_pv += fixed_payment * discount_factors[i]
            
            # Calculate present value of floating leg
            floating_leg_pv = 0.0
            for i, (rate, period) in enumerate(zip(floating_rates, floating_payment_periods)):
                if i < len(discount_factors):
                    floating_payment = notional * rate * period
                    floating_leg_pv += floating_payment * discount_factors[i]
            
            # Calculate swap value based on type
            if swap_type == "pay_fixed":
                # Pay fixed, receive floating: floating_pv - fixed_pv
                swap_value = floating_leg_pv - fixed_leg_pv
            elif swap_type == "receive_fixed":
                # Receive fixed, pay floating: fixed_pv - floating_pv
                swap_value = fixed_leg_pv - floating_leg_pv
            else:
                raise ValueError("swap_type must be 'pay_fixed' or 'receive_fixed'")
                
            return swap_value
            
        except (ZeroDivisionError, ValueError) as e:
            return None

    def calculate_fair_fixed_rate(
        self,
        floating_rates: List[float],
        notional: float,
        fixed_payment_periods: List[float],
        floating_payment_periods: List[float],
        discount_factors: List[float]
    ) -> Optional[float]:
        """
        Calculate the fair fixed rate that makes the swap have zero value at inception.
        
        Parameters
        ----------
        floating_rates : List[float]
            Expected floating rates for each payment period
        notional : float
            Notional amount of the swap
        fixed_payment_periods : List[float]
            Time periods (in years) for fixed leg payments
        floating_payment_periods : List[float]
            Time periods (in years) for floating leg payments
        discount_factors : List[float]
            Discount factors for each payment date
            
        Returns
        -------
        float | None
            Fair fixed rate
        """
        
        if not all([
            fixed_payment_periods, 
            floating_payment_periods, 
            floating_rates,
            discount_factors
        ]):
            return None

        try:
            # Calculate present value of floating leg
            floating_leg_pv = 0.0
            for i, (rate, period) in enumerate(zip(floating_rates, floating_payment_periods)):
                if i < len(discount_factors):
                    floating_payment = notional * rate * period
                    floating_leg_pv += floating_payment * discount_factors[i]
            
            # Calculate present value of fixed leg annuity (without rate)
            fixed_leg_annuity = 0.0
            for i, period in enumerate(fixed_payment_periods):
                if i < len(discount_factors):
                    fixed_leg_annuity += notional * period * discount_factors[i]
            
            if fixed_leg_annuity == 0:
                return None
                
            # Fair fixed rate = PV of floating leg / PV of fixed leg annuity
            fair_fixed_rate = floating_leg_pv / fixed_leg_annuity
            
            return fair_fixed_rate
            
        except (ZeroDivisionError, ValueError):
            return None