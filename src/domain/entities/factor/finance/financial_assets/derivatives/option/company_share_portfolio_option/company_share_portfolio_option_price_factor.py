import math
import random
from typing import List, Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_factor import CompanySharePortfolioOptionFactor


class CompanySharePortfolioOptionPriceFactor(CompanySharePortfolioOptionFactor):
    """Price factor associated with company share portfolio options."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
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
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
            **kwargs,
        )

    def calculate(
        self,
        stock_price: float,        # current stock price
        strike_price: float,       # strike price
        risk_free_rate: float,     # risk-free rate
        volatility: float,         # implied volatility
        time_to_expiry: float,     # time to expiration in years
        option_type: str = "call",
        dividend_yield: float = 0.0,  # dividend yield of underlying stock
        multiplier: int = 100,        # contract multiplier
    ) -> Optional[float]:
        """
        Calculate the theoretical company share portfolio option price using Black-Scholes formula.
        """
        if stock_price <= 0 or strike_price <= 0 or volatility <= 0 or time_to_expiry <= 0:
            return None

        # Adjust for dividend yield
        adjusted_stock = stock_price * math.exp(-dividend_yield * time_to_expiry)
        
        d1, d2 = self._d1_d2(adjusted_stock, strike_price, risk_free_rate, volatility, time_to_expiry)
        if d1 is None or d2 is None:
            return None

        discount_factor = math.exp(-risk_free_rate * time_to_expiry)

        if option_type.lower() == "call":
            price = adjusted_stock * self._norm_cdf(d1) - strike_price * discount_factor * self._norm_cdf(d2)
        else:  # put
            price = strike_price * discount_factor * self._norm_cdf(-d2) - adjusted_stock * self._norm_cdf(-d1)

        return price * multiplier

    def calculate_price_monte_carlo(
        self,
        stock_price: float,
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
        Calculate company share portfolio option price using Monte Carlo simulation.
        """
        if stock_price <= 0 or strike_price <= 0 or volatility <= 0 or time_to_expiry <= 0:
            return None

        payoffs: List[float] = []
        drift = risk_free_rate - dividend_yield - 0.5 * volatility**2
        
        for _ in range(n_paths):
            # Simulate end-of-period stock price
            z = random.gauss(0, 1)
            final_stock_price = stock_price * math.exp(drift * time_to_expiry + volatility * math.sqrt(time_to_expiry) * z)
            
            if option_type.lower() == "call":
                payoff = max(final_stock_price - strike_price, 0)
            else:
                payoff = max(strike_price - final_stock_price, 0)
            payoffs.append(payoff)

        discounted_payoff = math.exp(-risk_free_rate * time_to_expiry) * sum(payoffs) / n_paths
        return discounted_payoff * multiplier

    def calculate_price_binomial(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        option_type: str = "call",
        dividend_yield: float = 0.0,
        multiplier: int = 100,
        steps: int = 100,
    ) -> Optional[float]:
        """
        Calculate company share portfolio option price using binomial tree model.
        """
        if stock_price <= 0 or strike_price <= 0 or volatility <= 0 or time_to_expiry <= 0 or steps <= 0:
            return None

        dt = time_to_expiry / steps
        up_factor = math.exp(volatility * math.sqrt(dt))
        down_factor = 1 / up_factor
        
        # Risk-neutral probability adjusted for dividends
        prob_up = (math.exp((risk_free_rate - dividend_yield) * dt) - down_factor) / (up_factor - down_factor)
        prob_down = 1 - prob_up
        
        # Check for valid probabilities
        if prob_up < 0 or prob_up > 1:
            return None

        # Initialize price tree at maturity
        prices = []
        for i in range(steps + 1):
            final_price = stock_price * (up_factor ** (steps - i)) * (down_factor ** i)
            if option_type.lower() == "call":
                option_value = max(final_price - strike_price, 0)
            else:
                option_value = max(strike_price - final_price, 0)
            prices.append(option_value)

        # Backward induction
        for step in range(steps - 1, -1, -1):
            new_prices = []
            for i in range(step + 1):
                value = math.exp(-risk_free_rate * dt) * (prob_up * prices[i] + prob_down * prices[i + 1])
                new_prices.append(value)
            prices = new_prices

        return prices[0] * multiplier