import math
import random
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionBatesPriceFactor(CompanyShareOptionFactor):
    """Bates model (Heston with jump diffusion) price factor for company share options."""

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
        T: float,          # time to maturity in years
        v0: float,         # initial volatility squared
        kappa: float,      # mean reversion speed
        theta: float,      # long-term volatility squared
        xi: float,         # volatility of volatility
        rho: float,        # correlation between asset and volatility
        lambda_j: float,   # jump intensity (jumps per year)
        mu_j: float,       # mean jump size (log scale)
        sigma_j: float,    # jump volatility
        q: float = 0.0,    # dividend yield
        option_type: str = "call",
        n_paths: int = 50000,  # number of Monte Carlo paths
        n_steps: int = 252,    # number of time steps per year
    ) -> Optional[float]:
        """
        Calculate option price using Bates model (Heston + jump diffusion) via Monte Carlo.
        
        The Bates model extends Heston with jumps:
        dS = (r - q - lambda_j*k)*S*dt + sqrt(v)*S*dW1 + S*J*dN
        dv = kappa*(theta - v)*dt + xi*sqrt(v)*dW2
        
        Where:
        - dW1, dW2 have correlation rho
        - J ~ log-normal jump size: ln(1+J) ~ N(mu_j, sigma_j^2)
        - dN ~ Poisson(lambda_j*dt) jump counting process
        - k = E[J] = exp(mu_j + sigma_j^2/2) - 1 (jump compensation)
        """
        if S <= 0 or K <= 0 or T <= 0 or v0 <= 0 or kappa <= 0 or theta <= 0 or xi <= 0:
            return None
        if abs(rho) >= 1 or lambda_j < 0 or sigma_j < 0:
            return None

        try:
            dt = T / n_steps
            sqrt_dt = math.sqrt(dt)
            
            # Jump compensation term
            k = math.exp(mu_j + 0.5 * sigma_j * sigma_j) - 1
            
            payoffs = []
            
            for _ in range(n_paths):
                S_t = S
                v_t = v0
                
                for _ in range(n_steps):
                    # Generate correlated random numbers for diffusion
                    z1 = random.gauss(0, 1)
                    z2 = rho * z1 + math.sqrt(1 - rho * rho) * random.gauss(0, 1)
                    
                    # Ensure volatility remains positive
                    v_t = max(v_t, 0)
                    sqrt_v = math.sqrt(v_t) if v_t > 0 else 0
                    
                    # Generate jumps using Poisson process
                    n_jumps = self._poisson_random(lambda_j * dt)
                    jump_component = 1.0
                    
                    for _ in range(n_jumps):
                        # Log-normal jump size
                        jump_log = random.gauss(mu_j, sigma_j)
                        jump_component *= (1 + (math.exp(jump_log) - 1))
                    
                    # Update asset price with diffusion and jumps
                    drift = (r - q - lambda_j * k) * dt
                    diffusion = sqrt_v * sqrt_dt * z1
                    
                    S_t *= math.exp(drift - 0.5 * v_t * dt + diffusion) * jump_component
                    S_t = max(S_t, 0)  # Ensure price remains positive
                    
                    # Update volatility (same as Heston)
                    dv = kappa * (theta - v_t) * dt + xi * sqrt_v * sqrt_dt * z2
                    v_t += dv
                    v_t = max(v_t, 0)  # Absorption at zero boundary
                
                # Calculate payoff
                if option_type.lower() == "call":
                    payoff = max(S_t - K, 0)
                else:  # put
                    payoff = max(K - S_t, 0)
                
                payoffs.append(payoff)
            
            # Discount the expected payoff
            option_price = math.exp(-r * T) * sum(payoffs) / len(payoffs)
            return option_price

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def _poisson_random(self, rate: float) -> int:
        """Generate random number from Poisson distribution."""
        if rate <= 0:
            return 0
        
        # For small rates, use Knuth's algorithm
        if rate < 30:
            L = math.exp(-rate)
            k = 0
            p = 1.0
            
            while p > L:
                k += 1
                p *= random.random()
            
            return k - 1
        else:
            # For large rates, use normal approximation
            return max(0, int(random.gauss(rate, math.sqrt(rate)) + 0.5))

    def calculate_characteristic_function(
        self,
        u: complex,
        S: float,
        r: float,
        T: float,
        v0: float,
        kappa: float,
        theta: float,
        xi: float,
        rho: float,
        lambda_j: float,
        mu_j: float,
        sigma_j: float,
        q: float = 0.0,
    ) -> complex:
        """
        Calculate the characteristic function for the Bates model.
        Extends Heston characteristic function with jump component.
        """
        try:
            # Heston component (same as Heston characteristic function)
            d = math.sqrt((rho * xi * u * 1j - kappa) ** 2 + xi ** 2 * (u * 1j + u ** 2))
            g = (kappa - rho * xi * u * 1j - d) / (kappa - rho * xi * u * 1j + d)
            
            # Avoid numerical issues
            if abs(g) >= 1:
                return 0
            
            # Heston components
            C_heston = (kappa * theta / (xi ** 2)) * (
                (kappa - rho * xi * u * 1j - d) * T - 2 * math.log((1 - g * math.exp(-d * T)) / (1 - g))
            )
            
            D_heston = ((kappa - rho * xi * u * 1j - d) / (xi ** 2)) * (1 - math.exp(-d * T)) / (1 - g * math.exp(-d * T))
            
            # Jump component
            # E[exp(iu*ln(1+J))] = exp(iu*mu_j - 0.5*sigma_j^2*u^2)
            jump_cf = math.exp(u * 1j * mu_j - 0.5 * sigma_j ** 2 * u ** 2)
            
            # Jump compensation
            k = math.exp(mu_j + 0.5 * sigma_j * sigma_j) - 1
            
            # Total characteristic function
            C_total = C_heston + (r - q - lambda_j * k) * u * 1j * T + lambda_j * T * (jump_cf - 1)
            
            return math.exp(C_total + D_heston * v0 + u * 1j * math.log(S))

        except (ValueError, ZeroDivisionError, OverflowError):
            return 0

    def calculate_jump_risk_neutral_measure(
        self,
        lambda_j: float,
        mu_j: float,
        sigma_j: float,
        risk_premium: float = 0.0,
    ) -> dict:
        """
        Transform jump parameters to risk-neutral measure.
        
        Under risk-neutral measure, jump intensity and distribution may change.
        This is a simplified transformation.
        """
        try:
            # Adjust jump intensity for risk premium
            lambda_j_rn = lambda_j * math.exp(-risk_premium)
            
            # Adjust jump mean (simplified)
            mu_j_rn = mu_j - risk_premium
            
            # Jump volatility typically remains the same
            sigma_j_rn = sigma_j
            
            return {
                "lambda_j": lambda_j_rn,
                "mu_j": mu_j_rn,
                "sigma_j": sigma_j_rn
            }

        except (ValueError, OverflowError):
            return {
                "lambda_j": lambda_j,
                "mu_j": mu_j,
                "sigma_j": sigma_j
            }

    def calculate_jump_statistics(self, lambda_j: float, mu_j: float, sigma_j: float) -> dict:
        """Calculate statistics of the jump component."""
        try:
            # Expected jump size
            expected_jump = math.exp(mu_j + 0.5 * sigma_j * sigma_j) - 1
            
            # Jump variance
            jump_variance = (math.exp(sigma_j * sigma_j) - 1) * math.exp(2 * mu_j + sigma_j * sigma_j)
            
            # Skewness contribution from jumps
            exp_term = math.exp(mu_j + 0.5 * sigma_j * sigma_j)
            jump_skewness = lambda_j * exp_term * (exp_term * exp_term * (math.exp(sigma_j * sigma_j) - 1) + 3 * (math.exp(sigma_j * sigma_j) - 1) + 1)
            
            # Kurtosis contribution from jumps
            jump_kurtosis = lambda_j * exp_term * (
                exp_term ** 3 * (math.exp(sigma_j * sigma_j) - 1) * (math.exp(3 * sigma_j * sigma_j) + 6 * math.exp(2 * sigma_j * sigma_j) + 7 * math.exp(sigma_j * sigma_j) + 1) +
                6 * exp_term ** 2 * (math.exp(sigma_j * sigma_j) - 1) * (math.exp(2 * sigma_j * sigma_j) + 3 * math.exp(sigma_j * sigma_j) + 2) +
                7 * exp_term * (math.exp(sigma_j * sigma_j) - 1) +
                1
            )
            
            return {
                "expected_jump_size": expected_jump,
                "jump_variance": jump_variance,
                "jump_skewness": jump_skewness,
                "jump_kurtosis": jump_kurtosis,
                "jumps_per_year": lambda_j
            }

        except (ValueError, OverflowError):
            return {}