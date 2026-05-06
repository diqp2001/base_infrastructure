import math
from typing import Optional
import numpy as np

from domain.entities.factor.finance.portfolio.derivatives.option.company_share_option_portfolio.company_share_option_portfolio_factor import CompanyShareOptionPortfolioFactor


class CompanyShareOptionPortfolioBlackScholesMertonPriceFactor(CompanyShareOptionPortfolioFactor):
    """Black-Scholes-Merton price factor for company share option portfolios with dividend yield."""

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

    def calculate_black_scholes_merton_price(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        dividend_yield: float,
        option_type: str = "call",
    ) -> float:
        """
        Calculate option price using Black-Scholes-Merton model with dividend yield.
        
        Args:
            spot_price: Current price of the underlying portfolio
            strike_price: Strike price of the option
            time_to_expiry: Time to expiration in years
            risk_free_rate: Risk-free interest rate
            volatility: Volatility of the underlying portfolio
            dividend_yield: Dividend yield of the portfolio
            option_type: "call" or "put"
            
        Returns:
            Option price
        """
        if time_to_expiry <= 0:
            if option_type.lower() == "call":
                return max(0, spot_price - strike_price)
            else:
                return max(0, strike_price - spot_price)

        # Adjust spot price for dividend yield
        adj_spot_price = spot_price * math.exp(-dividend_yield * time_to_expiry)
        
        d1 = (math.log(adj_spot_price / strike_price) + 
              (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / (
              volatility * math.sqrt(time_to_expiry)
        )
        
        d2 = d1 - volatility * math.sqrt(time_to_expiry)
        
        # Normal cumulative distribution function
        from scipy.stats import norm
        
        if option_type.lower() == "call":
            price = (adj_spot_price * norm.cdf(d1) - 
                    strike_price * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2))
        else:
            price = (strike_price * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2) - 
                    adj_spot_price * norm.cdf(-d1))
            
        return max(0, price)

    def calculate_greeks(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        dividend_yield: float,
        option_type: str = "call",
    ) -> dict:
        """
        Calculate option Greeks using Black-Scholes-Merton model.
        
        Returns:
            Dictionary containing delta, gamma, theta, vega, and rho
        """
        if time_to_expiry <= 0:
            return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0, "rho": 0}

        # Adjust spot price for dividend yield
        adj_spot_price = spot_price * math.exp(-dividend_yield * time_to_expiry)
        
        d1 = (math.log(adj_spot_price / strike_price) + 
              (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / (
              volatility * math.sqrt(time_to_expiry)
        )
        
        d2 = d1 - volatility * math.sqrt(time_to_expiry)
        
        from scipy.stats import norm
        
        # Greeks calculations
        if option_type.lower() == "call":
            delta = math.exp(-dividend_yield * time_to_expiry) * norm.cdf(d1)
        else:
            delta = -math.exp(-dividend_yield * time_to_expiry) * norm.cdf(-d1)
            
        gamma = (math.exp(-dividend_yield * time_to_expiry) * norm.pdf(d1)) / (
            spot_price * volatility * math.sqrt(time_to_expiry)
        )
        
        if option_type.lower() == "call":
            theta = ((-spot_price * norm.pdf(d1) * volatility * math.exp(-dividend_yield * time_to_expiry)) / 
                    (2 * math.sqrt(time_to_expiry)) - 
                    risk_free_rate * strike_price * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2) +
                    dividend_yield * spot_price * math.exp(-dividend_yield * time_to_expiry) * norm.cdf(d1))
        else:
            theta = ((-spot_price * norm.pdf(d1) * volatility * math.exp(-dividend_yield * time_to_expiry)) / 
                    (2 * math.sqrt(time_to_expiry)) + 
                    risk_free_rate * strike_price * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2) -
                    dividend_yield * spot_price * math.exp(-dividend_yield * time_to_expiry) * norm.cdf(-d1))
        
        vega = spot_price * math.exp(-dividend_yield * time_to_expiry) * norm.pdf(d1) * math.sqrt(time_to_expiry)
        
        if option_type.lower() == "call":
            rho = strike_price * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2)
        else:
            rho = -strike_price * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2)
        
        return {
            "delta": delta,
            "gamma": gamma,
            "theta": theta / 365,  # Convert to per-day
            "vega": vega / 100,   # Convert to per-percent
            "rho": rho / 100      # Convert to per-percent
        }