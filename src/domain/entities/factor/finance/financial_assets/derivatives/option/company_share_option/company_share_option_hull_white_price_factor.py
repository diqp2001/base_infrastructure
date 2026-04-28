import math
import random
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionHullWhitePriceFactor(CompanyShareOptionFactor):
    """Hull-White stochastic interest rate price factor for company share options."""

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
        r0: float,         # initial interest rate
        T: float,          # time to maturity in years
        sigma: float,      # asset volatility
        a: float,          # mean reversion speed for interest rate
        sigma_r: float,    # interest rate volatility
        rho: float,        # correlation between asset and interest rate
        q: float = 0.0,    # dividend yield
        option_type: str = "call",
        n_paths: int = 50000,  # number of Monte Carlo paths
        n_steps: int = 252,    # number of time steps per year
    ) -> Optional[float]:
        """
        Calculate option price using Hull-White stochastic interest rate model via Monte Carlo.
        
        The Hull-White model assumes:
        dS = (r(t) - q)*S*dt + sigma*S*dW1
        dr = a*(theta(t) - r)*dt + sigma_r*dW2
        
        Where dW1 and dW2 have correlation rho, and theta(t) is calibrated to match
        the current term structure.
        """
        if S <= 0 or K <= 0 or T <= 0 or sigma <= 0 or a <= 0 or sigma_r <= 0:
            return None
        if abs(rho) >= 1:
            return None

        try:
            dt = T / n_steps
            sqrt_dt = math.sqrt(dt)
            
            payoffs = []
            
            for _ in range(n_paths):
                S_t = S
                r_t = r0
                
                for _ in range(n_steps):
                    # Generate correlated random numbers
                    z1 = random.gauss(0, 1)
                    z2 = rho * z1 + math.sqrt(1 - rho * rho) * random.gauss(0, 1)
                    
                    # For simplicity, assume theta(t) = r0 (flat term structure)
                    # In practice, theta(t) would be calibrated to market data
                    theta_t = r0
                    
                    # Update interest rate using Vasicek process
                    dr = a * (theta_t - r_t) * dt + sigma_r * sqrt_dt * z2
                    r_t += dr
                    
                    # Update asset price
                    dS = (r_t - q) * S_t * dt + sigma * S_t * sqrt_dt * z1
                    S_t += dS
                    S_t = max(S_t, 0)  # Ensure price remains positive
                
                # Calculate payoff
                if option_type.lower() == "call":
                    payoff = max(S_t - K, 0)
                else:  # put
                    payoff = max(K - S_t, 0)
                
                payoffs.append(payoff)
            
            # Discount using average interest rate path
            # Note: This is a simplification; proper implementation would use
            # the stochastic discount factor
            avg_r = sum(self._get_avg_rate_path(r0, a, sigma_r, T, n_steps) for _ in range(1000)) / 1000
            option_price = math.exp(-avg_r * T) * sum(payoffs) / len(payoffs)
            return option_price

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def _get_avg_rate_path(self, r0: float, a: float, sigma_r: float, T: float, n_steps: int) -> float:
        """Calculate average interest rate over one path."""
        dt = T / n_steps
        sqrt_dt = math.sqrt(dt)
        r_t = r0
        rate_sum = r0
        
        for _ in range(n_steps):
            dr = a * (r0 - r_t) * dt + sigma_r * sqrt_dt * random.gauss(0, 1)
            r_t += dr
            rate_sum += r_t
        
        return rate_sum / (n_steps + 1)

    def calculate_bond_option(
        self,
        F: float,          # forward bond price
        K: float,          # strike price
        T: float,          # time to maturity
        sigma_P: float,    # bond price volatility
        r0: float,         # initial interest rate
        option_type: str = "call",
    ) -> Optional[float]:
        """
        Calculate bond option price using Hull-White model (Black-76 approximation).
        
        This is used when pricing options on bonds within the Hull-White framework.
        """
        if F <= 0 or K <= 0 or T <= 0 or sigma_P <= 0:
            return None

        try:
            d1 = (math.log(F / K) + 0.5 * sigma_P ** 2 * T) / (sigma_P * math.sqrt(T))
            d2 = d1 - sigma_P * math.sqrt(T)

            if option_type.lower() == "call":
                price = math.exp(-r0 * T) * (F * self._norm_cdf(d1) - K * self._norm_cdf(d2))
            else:  # put
                price = math.exp(-r0 * T) * (K * self._norm_cdf(-d2) - F * self._norm_cdf(-d1))

            return price

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def calculate_caplet_floorlet(
        self,
        L: float,          # forward LIBOR rate
        K: float,          # strike rate
        T: float,          # time to maturity
        delta: float,      # accrual period
        N: float,          # notional amount
        sigma_L: float,    # LIBOR volatility
        r0: float,         # initial interest rate
        option_type: str = "caplet",  # caplet or floorlet
    ) -> Optional[float]:
        """
        Calculate caplet/floorlet price using Hull-White model (Black formula for rates).
        
        Caplet: max(L - K, 0) * delta * N * DF
        Floorlet: max(K - L, 0) * delta * N * DF
        """
        if L <= 0 or K <= 0 or T <= 0 or sigma_L <= 0 or delta <= 0 or N <= 0:
            return None

        try:
            d1 = (math.log(L / K) + 0.5 * sigma_L ** 2 * T) / (sigma_L * math.sqrt(T))
            d2 = d1 - sigma_L * math.sqrt(T)

            discount_factor = math.exp(-r0 * (T + delta))

            if option_type.lower() == "caplet":
                price = N * delta * discount_factor * (L * self._norm_cdf(d1) - K * self._norm_cdf(d2))
            else:  # floorlet
                price = N * delta * discount_factor * (K * self._norm_cdf(-d2) - L * self._norm_cdf(-d1))

            return price

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def _norm_cdf(self, x: float) -> float:
        """Standard normal cumulative distribution function."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def calibrate_theta(self, market_rates: list, times: list, a: float, sigma_r: float) -> list:
        """
        Calibrate theta(t) function to match market forward rates.
        
        This is a simplified implementation. In practice, more sophisticated
        numerical methods would be used.
        """
        if len(market_rates) != len(times):
            return []

        theta_values = []
        for i, (rate, time) in enumerate(zip(market_rates, times)):
            if i == 0:
                theta_t = rate
            else:
                # Simplified calculation for theta(t)
                prev_rate = market_rates[i-1]
                dt = time - times[i-1] if i > 0 else time
                
                # Approximate theta using forward rate evolution
                theta_t = rate + (sigma_r ** 2) / (2 * a) * (1 - math.exp(-2 * a * time))
            
            theta_values.append(theta_t)

        return theta_values