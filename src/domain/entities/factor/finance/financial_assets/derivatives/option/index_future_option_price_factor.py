import math
import random
from typing import List, Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_factor import IndexFutureOptionFactor


class IndexFutureOptionPriceFactor(IndexFutureOptionFactor):
    """Price factor associated with index future options."""

    def __init__(
        self,
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            factor_id=factor_id,
            **kwargs
        )

    def calculate_price(
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
        Calculate the theoretical index future option price using Black-Scholes formula
        adapted for index options with dividend yield.
        """
        if index_level <= 0 or strike_price <= 0 or volatility <= 0 or time_to_expiry <= 0:
            return None

        # Adjust for dividend yield
        adjusted_index = index_level * math.exp(-dividend_yield * time_to_expiry)
        
        d1, d2 = self._d1_d2(adjusted_index, strike_price, risk_free_rate, volatility, time_to_expiry)
        if d1 is None or d2 is None:
            return None

        discount_factor = math.exp(-risk_free_rate * time_to_expiry)

        if option_type.lower() == "call":
            price = adjusted_index * self._norm_cdf(d1) - strike_price * discount_factor * self._norm_cdf(d2)
        else:  # put
            price = strike_price * discount_factor * self._norm_cdf(-d2) - adjusted_index * self._norm_cdf(-d1)

        return price * multiplier

    def calculate_price_monte_carlo(
        self,
        index_level: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        option_type: str = "call",
        dividend_yield: float = 0.0,
        multiplier: int = 100,
        n_paths: int = 10000,
    ) -> Optional[float]:
        """
        Calculate index future option price using Monte Carlo simulation.
        """
        if index_level <= 0 or strike_price <= 0 or volatility <= 0 or time_to_expiry <= 0:
            return None

        payoffs: List[float] = []
        drift = risk_free_rate - dividend_yield - 0.5 * volatility**2
        
        for _ in range(n_paths):
            # Simulate end-of-period index level
            z = random.gauss(0, 1)
            final_index = index_level * math.exp(drift * time_to_expiry + volatility * math.sqrt(time_to_expiry) * z)
            
            if option_type.lower() == "call":
                payoff = max(final_index - strike_price, 0)
            else:
                payoff = max(strike_price - final_index, 0)
            payoffs.append(payoff)

        discounted_payoff = math.exp(-risk_free_rate * time_to_expiry) * sum(payoffs) / n_paths
        return discounted_payoff * multiplier