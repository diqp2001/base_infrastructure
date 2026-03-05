import math
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_factor import IndexFutureOptionFactor


class IndexFutureOptionDeltaFactor(IndexFutureOptionFactor):
    """Delta factor associated with index future options."""

    def __init__(
        self,
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            factor_id=factor_id,
            **kwargs
        )

    def calculate_delta(
        self,
        index_level: float,     # current index level
        strike_price: float,    # strike price
        risk_free_rate: float,  # risk-free rate
        volatility: float,      # implied volatility
        time_to_expiry: float,  # time to expiration in years
        option_type: str = "call",
        dividend_yield: float = 0.0,  # dividend yield of underlying index
        multiplier: int = 100,        # contract multiplier
    ) -> Optional[float]:
        """
        Calculate delta for index future options using Black-Scholes model
        adapted for index options with dividend yield.
        """
        if index_level <= 0 or strike_price <= 0 or volatility <= 0 or time_to_expiry <= 0:
            return None

        # Adjust for dividend yield
        adjusted_index = index_level * math.exp(-dividend_yield * time_to_expiry)
        
        d1, d2 = self._d1_d2(adjusted_index, strike_price, risk_free_rate, volatility, time_to_expiry)
        if d1 is None:
            return None

        dividend_discount = math.exp(-dividend_yield * time_to_expiry)

        if option_type.lower() == "call":
            delta = dividend_discount * self._norm_cdf(d1)
        else:  # put
            delta = dividend_discount * (self._norm_cdf(d1) - 1)

        return delta * multiplier

    def calculate_dollar_delta(
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
        Calculate dollar delta (delta * index level * multiplier).
        Represents the dollar change in option value for a 1 point move in the index.
        """
        delta = self.calculate_delta(
            index_level, strike_price, risk_free_rate, volatility,
            time_to_expiry, option_type, dividend_yield, multiplier
        )
        if delta is None:
            return None
            
        return delta * index_level

    def calculate_hedge_ratio(
        self,
        index_level: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        option_type: str = "call",
        dividend_yield: float = 0.0,
        multiplier: int = 100,
        hedge_instrument_multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate hedge ratio for hedging option position with underlying index futures.
        
        Args:
            hedge_instrument_multiplier: Multiplier of the hedging instrument
            
        Returns:
            Number of hedge instrument contracts needed per option contract
        """
        delta = self.calculate_delta(
            index_level, strike_price, risk_free_rate, volatility,
            time_to_expiry, option_type, dividend_yield, multiplier
        )
        if delta is None:
            return None
            
        return (delta * multiplier) / hedge_instrument_multiplier