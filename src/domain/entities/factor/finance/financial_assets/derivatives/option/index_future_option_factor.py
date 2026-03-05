from __future__ import annotations
import math
from typing import Optional, Union
from datetime import timedelta

from src.domain.entities.factor.finance.financial_assets.derivatives.option.option_factor import OptionFactor


class IndexFutureOptionFactor(OptionFactor):
    """Domain factor representing index future option-specific characteristics."""

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
        strike_price: Optional[float] = None,
        multiplier: Optional[int] = None,
        index_symbol: Optional[str] = None,

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
        )
        
        # Index future option specific attributes
        self.strike_price = strike_price
        self.multiplier = multiplier
        self.index_symbol = index_symbol

    def calculate_index_future_option_value(
        self,
        index_level: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        option_type: str = "call",
        dividend_yield: float = 0.0,
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate index future option value using Black-Scholes model adapted for index options.
        
        Args:
            index_level: Current index level
            strike_price: Strike price of the option
            risk_free_rate: Risk-free interest rate
            volatility: Implied volatility
            time_to_expiry: Time to expiration in years
            option_type: "call" or "put"
            dividend_yield: Dividend yield of the underlying index
            multiplier: Contract multiplier (default 100)
            
        Returns:
            Index future option value or None if calculation fails
        """
        if index_level <= 0 or strike_price <= 0 or volatility <= 0 or time_to_expiry <= 0:
            return None

        # Adjust for dividend yield in index options
        adjusted_index_level = index_level * math.exp(-dividend_yield * time_to_expiry)
        
        d1, d2 = self._d1_d2(adjusted_index_level, strike_price, risk_free_rate, volatility, time_to_expiry)
        if d1 is None or d2 is None:
            return None

        if option_type.lower() == "call":
            option_value = (adjusted_index_level * self._norm_cdf(d1) - 
                          strike_price * math.exp(-risk_free_rate * time_to_expiry) * self._norm_cdf(d2))
        else:  # put
            option_value = (strike_price * math.exp(-risk_free_rate * time_to_expiry) * self._norm_cdf(-d2) - 
                          adjusted_index_level * self._norm_cdf(-d1))

        return option_value * multiplier