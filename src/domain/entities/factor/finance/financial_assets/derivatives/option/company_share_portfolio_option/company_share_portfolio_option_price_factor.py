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

    @property
    def calculate_dependencies(self) -> list:
        return ["CompanySharePortfolioValueFactor"]

    def calculate(self, dependencies: dict) -> Optional[float]:
        """
        Calculate the theoretical portfolio option price using Black-Scholes.

        Reads portfolio value from resolved dependency; all other BSM inputs use
        sensible defaults that can be overridden by including them in the dependencies
        dict (e.g. strike_price, time_to_expiry, option_type, risk_free_rate,
        dividend_yield, multiplier).
        """
        stock_price    = dependencies.get("CompanySharePortfolioValueFactor")
        volatility     = dependencies.get("implied_volatility", 0.20)
        strike_price   = dependencies.get("strike_price")
        time_to_expiry = float(dependencies.get("time_to_expiry", 30 / 365))
        option_type    = dependencies.get("option_type", "call")
        risk_free_rate = float(dependencies.get("risk_free_rate", 0.05))
        dividend_yield = float(dependencies.get("dividend_yield", 0.0))
        multiplier     = int(dependencies.get("multiplier", 100))

        if stock_price is None or stock_price <= 0:
            return None
        if volatility <= 0 or time_to_expiry <= 0:
            return None
        if strike_price is None:
            strike_price = stock_price  # ATM default when strike unknown

        return self._bsm_price(
            stock_price, strike_price, risk_free_rate, volatility,
            time_to_expiry, option_type, dividend_yield, multiplier,
        )

    def _norm_cdf(self, x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

    def _d1_d2(self, S, K, r, sigma, T):
        try:
            d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            return d1, d2
        except (ValueError, ZeroDivisionError):
            return None, None

    def _bsm_price(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        option_type: str = "call",
        dividend_yield: float = 0.0,
        multiplier: int = 100,
    ) -> Optional[float]:
        """Black-Scholes-Merton price (internal helper)."""
        if stock_price <= 0 or strike_price <= 0 or volatility <= 0 or time_to_expiry <= 0:
            return None

        adjusted_stock = stock_price * math.exp(-dividend_yield * time_to_expiry)
        d1, d2 = self._d1_d2(adjusted_stock, strike_price, risk_free_rate, volatility, time_to_expiry)
        if d1 is None or d2 is None:
            return None

        discount_factor = math.exp(-risk_free_rate * time_to_expiry)

        if option_type.lower() == "call":
            price = adjusted_stock * self._norm_cdf(d1) - strike_price * discount_factor * self._norm_cdf(d2)
        else:
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