import math
import random
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_factor import PortfolioCompanyShareOptionFactor


class PortfolioCompanyShareOptionHestonPriceFactor(PortfolioCompanyShareOptionFactor):
    """Heston stochastic volatility price factor for portfolio company share options."""

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
        S: float,          # underlying portfolio price/level
        K: float,          # strike price
        r: float,          # risk-free rate
        T: float,          # time to maturity in years
        v0: float,         # initial volatility squared
        kappa: float,      # mean reversion speed
        theta: float,      # long-term volatility squared
        xi: float,         # volatility of volatility
        rho: float,        # correlation between portfolio and volatility
        q: float = 0.0,    # portfolio dividend yield
        option_type: str = "call",
        multiplier: int = 100,
        n_paths: int = 50000,  # number of Monte Carlo paths
        n_steps: int = 252,    # number of time steps per year
    ) -> Optional[float]:
        """
        Calculate portfolio option price using Heston stochastic volatility model via Monte Carlo.
        
        For portfolio options, the underlying follows:
        dS = (r - q)*S*dt + sqrt(v)*S*dW1
        dv = kappa*(theta - v)*dt + xi*sqrt(v)*dW2
        
        Where dW1 and dW2 have correlation rho, and S represents the portfolio value/level.
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
                    
                    # Update portfolio price
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
            return option_price * multiplier

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def calculate_multi_asset_heston(
        self,
        spot_prices: list,     # [S1, S2, ..., Sn] individual asset prices
        weights: list,         # [w1, w2, ..., wn] portfolio weights
        K: float,              # strike price
        r: float,              # risk-free rate
        T: float,              # time to maturity
        v0_assets: list,       # [v0_1, v0_2, ..., v0_n] initial variances
        kappa_assets: list,    # [κ1, κ2, ..., κn] mean reversion speeds
        theta_assets: list,    # [θ1, θ2, ..., θn] long-term variances
        xi_assets: list,       # [ξ1, ξ2, ..., ξn] volatilities of volatilities
        correlations: list,    # correlation matrix for assets and volatilities
        dividend_yields: list = None,
        option_type: str = "call",
        multiplier: int = 100,
        n_paths: int = 25000,
        n_steps: int = 252,
    ) -> Optional[float]:
        """
        Calculate multi-asset portfolio option price with individual Heston processes.
        
        Each asset follows its own Heston process, with correlations between
        asset returns and volatility processes.
        """
        n_assets = len(spot_prices)
        if (len(weights) != n_assets or len(v0_assets) != n_assets or 
            len(kappa_assets) != n_assets or len(theta_assets) != n_assets or len(xi_assets) != n_assets):
            return None

        if dividend_yields is None:
            dividend_yields = [0.0] * n_assets

        try:
            dt = T / n_steps
            sqrt_dt = math.sqrt(dt)
            
            payoffs = []
            
            for _ in range(n_paths):
                S_t = spot_prices.copy()
                v_t = v0_assets.copy()
                
                for _ in range(n_steps):
                    # Generate correlated random numbers (simplified correlation structure)
                    z = [random.gauss(0, 1) for _ in range(2 * n_assets)]
                    
                    # Update each asset and its volatility
                    for i in range(n_assets):
                        # Ensure volatility remains positive
                        v_t[i] = max(v_t[i], 0)
                        sqrt_v = math.sqrt(v_t[i]) if v_t[i] > 0 else 0
                        
                        # Update asset price
                        dS = (r - dividend_yields[i]) * S_t[i] * dt + sqrt_v * S_t[i] * sqrt_dt * z[i]
                        S_t[i] += dS
                        S_t[i] = max(S_t[i], 0)
                        
                        # Update volatility
                        dv = kappa_assets[i] * (theta_assets[i] - v_t[i]) * dt + xi_assets[i] * sqrt_v * sqrt_dt * z[i + n_assets]
                        v_t[i] += dv
                        v_t[i] = max(v_t[i], 0)
                
                # Calculate portfolio value
                portfolio_value = sum(w * S for w, S in zip(weights, S_t))
                
                # Calculate payoff
                if option_type.lower() == "call":
                    payoff = max(portfolio_value - K, 0)
                else:  # put
                    payoff = max(K - portfolio_value, 0)
                
                payoffs.append(payoff)
            
            # Discount the expected payoff
            option_price = math.exp(-r * T) * sum(payoffs) / len(payoffs)
            return option_price * multiplier

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def calculate_variance_swap_rate(
        self,
        v0: float,         # initial volatility squared
        kappa: float,      # mean reversion speed
        theta: float,      # long-term volatility squared
        T: float,          # time to maturity
    ) -> Optional[float]:
        """
        Calculate the fair variance swap rate under Heston model.
        
        For a variance swap, the fair strike is the expected average variance:
        E[∫₀ᵀ v_t dt] / T
        """
        if v0 <= 0 or kappa <= 0 or theta <= 0 or T <= 0:
            return None

        try:
            # Analytical formula for expected variance under Heston
            if abs(kappa) < 1e-10:
                expected_variance = v0
            else:
                expected_variance = theta + (v0 - theta) * (1 - math.exp(-kappa * T)) / (kappa * T)

            return expected_variance

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def calculate_volatility_surface_fit(
        self,
        market_prices: dict,  # {(K, T): market_price}
        S0: float,            # current portfolio level
        r: float,             # risk-free rate
        q: float = 0.0,       # dividend yield
        initial_guess: dict = None,
    ) -> dict:
        """
        Calibrate Heston parameters to fit market option prices.
        
        This is a simplified implementation for demonstration purposes.
        """
        if initial_guess is None:
            initial_guess = {
                "v0": 0.04,      # 20% initial volatility
                "kappa": 2.0,    # mean reversion speed
                "theta": 0.04,   # long-term variance
                "xi": 0.3,       # vol of vol
                "rho": -0.5      # correlation
            }

        # This would typically use optimization methods like differential evolution
        # For now, return the initial guess as a placeholder
        return initial_guess

    def feller_condition_check(self, kappa: float, theta: float, xi: float) -> bool:
        """
        Check if Feller condition is satisfied: 2*kappa*theta >= xi^2
        This ensures the volatility process doesn't reach zero.
        """
        return 2 * kappa * theta >= xi * xi

    def calculate_moment_generating_function(
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
        Calculate the moment generating function for portfolio returns under Heston.
        """
        try:
            # This is the same as the characteristic function calculation
            d = math.sqrt((rho * xi * u * 1j - kappa) ** 2 + xi ** 2 * (u * 1j + u ** 2))
            g = (kappa - rho * xi * u * 1j - d) / (kappa - rho * xi * u * 1j + d)
            
            # Avoid numerical issues
            if abs(g) >= 1:
                return 0
            
            # MGF components
            C = (r - q) * u * 1j * T + (kappa * theta / (xi ** 2)) * (
                (kappa - rho * xi * u * 1j - d) * T - 2 * math.log((1 - g * math.exp(-d * T)) / (1 - g))
            )
            
            D = ((kappa - rho * xi * u * 1j - d) / (xi ** 2)) * (1 - math.exp(-d * T)) / (1 - g * math.exp(-d * T))
            
            return math.exp(C + D * v0 + u * 1j * math.log(S))

        except (ValueError, ZeroDivisionError, OverflowError):
            return 0