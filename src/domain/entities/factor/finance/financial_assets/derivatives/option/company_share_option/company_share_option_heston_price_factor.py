import math
import random
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionHestonPriceFactor(CompanyShareOptionFactor):
    """Heston stochastic volatility price factor for company share options."""

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
        q: float = 0.0,    # dividend yield
        option_type: str = "call",
        n_paths: int = 50000,  # number of Monte Carlo paths
        n_steps: int = 252,    # number of time steps per year
    ) -> Optional[float]:
        """
        Calculate option price using Heston stochastic volatility model via Monte Carlo.
        
        The Heston model assumes:
        dS = (r - q)*S*dt + sqrt(v)*S*dW1
        dv = kappa*(theta - v)*dt + xi*sqrt(v)*dW2
        
        Where dW1 and dW2 have correlation rho.
        """
        if S <= 0 or K <= 0 or T <= 0 or v0 <= 0 or kappa <= 0 or theta <= 0 or xi <= 0:
            return None
        if abs(rho) >= 1:
            return None

        try:
            dt = T / n_steps
            sqrt_dt = math.sqrt(dt)
            
            payoffs = []
            
            for _ in range(n_paths):
                S_t = S
                v_t = v0
                
                for _ in range(n_steps):
                    # Generate correlated random numbers
                    z1 = random.gauss(0, 1)
                    z2 = rho * z1 + math.sqrt(1 - rho * rho) * random.gauss(0, 1)
                    
                    # Ensure volatility remains positive (Feller condition)
                    v_t = max(v_t, 0)
                    sqrt_v = math.sqrt(v_t) if v_t > 0 else 0
                    
                    # Update asset price
                    dS = (r - q) * S_t * dt + sqrt_v * S_t * sqrt_dt * z1
                    S_t += dS
                    S_t = max(S_t, 0)  # Ensure price remains positive
                    
                    # Update volatility (Euler-Maruyama scheme with absorption at zero)
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

    def calculate_with_milstein(
        self,
        S: float,
        K: float,
        r: float,
        T: float,
        v0: float,
        kappa: float,
        theta: float,
        xi: float,
        rho: float,
        q: float = 0.0,
        option_type: str = "call",
        n_paths: int = 50000,
        n_steps: int = 252,
    ) -> Optional[float]:
        """
        Calculate option price using Heston model with Milstein scheme for better accuracy.
        """
        if S <= 0 or K <= 0 or T <= 0 or v0 <= 0 or kappa <= 0 or theta <= 0 or xi <= 0:
            return None
        if abs(rho) >= 1:
            return None

        try:
            dt = T / n_steps
            sqrt_dt = math.sqrt(dt)
            
            payoffs = []
            
            for _ in range(n_paths):
                S_t = S
                v_t = v0
                
                for _ in range(n_steps):
                    # Generate correlated random numbers
                    z1 = random.gauss(0, 1)
                    z2 = rho * z1 + math.sqrt(1 - rho * rho) * random.gauss(0, 1)
                    
                    # Ensure volatility remains positive
                    v_t = max(v_t, 0)
                    sqrt_v = math.sqrt(v_t) if v_t > 0 else 0
                    
                    # Update asset price (geometric Brownian motion)
                    S_t *= math.exp((r - q - 0.5 * v_t) * dt + sqrt_v * sqrt_dt * z1)
                    
                    # Update volatility with Milstein scheme
                    dW2 = sqrt_dt * z2
                    v_t += (kappa * (theta - v_t) * dt + 
                           xi * sqrt_v * dW2 + 
                           0.25 * xi * xi * (dW2 * dW2 - dt))
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

    def feller_condition_check(self, kappa: float, theta: float, xi: float) -> bool:
        """
        Check if Feller condition is satisfied: 2*kappa*theta >= xi^2
        This ensures the volatility process doesn't reach zero.
        """
        return 2 * kappa * theta >= xi * xi

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
        q: float = 0.0,
    ) -> complex:
        """
        Calculate the characteristic function for the Heston model.
        Used in semi-analytical pricing methods.
        """
        try:
            # Constants
            d = math.sqrt((rho * xi * u * 1j - kappa) ** 2 + xi ** 2 * (u * 1j + u ** 2))
            g = (kappa - rho * xi * u * 1j - d) / (kappa - rho * xi * u * 1j + d)
            
            # Avoid numerical issues
            if abs(g) >= 1:
                return 0
            
            # Characteristic function components
            C = (r - q) * u * 1j * T + (kappa * theta / (xi ** 2)) * (
                (kappa - rho * xi * u * 1j - d) * T - 2 * math.log((1 - g * math.exp(-d * T)) / (1 - g))
            )
            
            D = ((kappa - rho * xi * u * 1j - d) / (xi ** 2)) * (1 - math.exp(-d * T)) / (1 - g * math.exp(-d * T))
            
            return math.exp(C + D * v0 + u * 1j * math.log(S))

        except (ValueError, ZeroDivisionError, OverflowError):
            return 0