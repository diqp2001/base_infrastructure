import math
from typing import Optional
import numpy as np

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionBlackScholesMertonPriceFactor(CompanyShareOptionFactor):
    """Black-Scholes-Merton price factor for company share options with dividend yield."""

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
        S: float,          # underlying price
        K: float,          # strike price
        r: float,          # risk-free rate
        sigma: float,      # volatility
        T: float,          # time to maturity in years
        q: float = 0.0,    # dividend yield
        option_type: str = "call",
    ) -> Optional[float]:
        """
        Calculate option price using Black-Scholes-Merton formula with dividend yield.
        
        The BSM formula extends Black-Scholes to include continuous dividend yield:
        - Call: S*e^(-q*T)*N(d1) - K*e^(-r*T)*N(d2)
        - Put: K*e^(-r*T)*N(-d2) - S*e^(-q*T)*N(-d1)
        
        Where:
        d1 = [ln(S/K) + (r - q + σ²/2)*T] / (σ*√T)
        d2 = d1 - σ*√T
        """
        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return None

        try:
            # Calculate d1 and d2 with dividend yield adjustment
            d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)

            # Calculate option price with dividend adjustment
            if option_type.lower() == "call":
                price = (S * math.exp(-q * T) * self._norm_cdf(d1) - 
                        K * math.exp(-r * T) * self._norm_cdf(d2))
            else:  # put
                price = (K * math.exp(-r * T) * self._norm_cdf(-d2) - 
                        S * math.exp(-q * T) * self._norm_cdf(-d1))

            return price

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def _norm_cdf(self, x: float) -> float:
        """Standard normal cumulative distribution function."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def calculate_greeks(
        self,
        S: float,
        K: float,
        r: float,
        sigma: float,
        T: float,
        q: float = 0.0,
        option_type: str = "call",
    ) -> dict:
        """Calculate option Greeks for BSM model."""
        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return {}

        try:
            d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            
            nd1 = self._norm_cdf(d1)
            nd2 = self._norm_cdf(d2)
            n_prime_d1 = self._norm_pdf(d1)
            
            if option_type.lower() == "call":
                delta = math.exp(-q * T) * nd1
                theta = (-(S * n_prime_d1 * sigma * math.exp(-q * T)) / (2 * math.sqrt(T)) - 
                        r * K * math.exp(-r * T) * nd2 + q * S * math.exp(-q * T) * nd1)
                rho = K * T * math.exp(-r * T) * nd2
            else:  # put
                delta = math.exp(-q * T) * (nd1 - 1)
                theta = (-(S * n_prime_d1 * sigma * math.exp(-q * T)) / (2 * math.sqrt(T)) + 
                        r * K * math.exp(-r * T) * self._norm_cdf(-d2) - q * S * math.exp(-q * T) * self._norm_cdf(-d1))
                rho = -K * T * math.exp(-r * T) * self._norm_cdf(-d2)
            
            gamma = (n_prime_d1 * math.exp(-q * T)) / (S * sigma * math.sqrt(T))
            vega = S * math.exp(-q * T) * n_prime_d1 * math.sqrt(T)
            
            return {
                "delta": delta,
                "gamma": gamma,
                "theta": theta,
                "vega": vega,
                "rho": rho
            }

        except (ValueError, ZeroDivisionError, OverflowError):
            return {}

    def _norm_pdf(self, x: float) -> float:
        """Standard normal probability density function."""
        return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)