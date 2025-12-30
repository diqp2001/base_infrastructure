import math
import random
from typing import List, Optional

from domain.entities.factor.finance.financial_assets.derivatives.option.option_factor import OptionFactor

class OptionPriceFactor(OptionFactor):
    """Price factor associated with a company share option."""

    def __init__(
        self,
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name="Option Price",
            group="Option Factor",
            subgroup="Price",
            data_type="float",
            source="model",
            definition="Theoretical option price calculated using Black-Scholes model.",
            factor_id=factor_id,
            **kwargs,
        )

    def calculate_price(
        self,
        S: float,          # underlying price
        K: float,          # strike
        r: float,          # risk-free rate
        sigma: float,      # volatility
        T: float,          # time to maturity in years
        option_type: str = "call",
    ) -> Optional[float]:
        """
        Calculate the theoretical option price using Black-Scholes formula.
        """
        d1, d2 = self._d1_d2(S, K, r, sigma, T)
        if d1 is None or d2 is None:
            return None

        if option_type.lower() == "call":
            price = S * self._norm_cdf(d1) - K * math.exp(-r * T) * self._norm_cdf(d2)
        else:  # put
            price = K * math.exp(-r * T) * self._norm_cdf(-d2) - S * self._norm_cdf(-d1)

        return price
    
      

    def calculate_price_sde(
        self,
        S: float,
        K: float,
        r: float,
        sigma: float,
        T: float,
        option_type: str = "call",
        n_paths: int = 10000,
    ) -> Optional[float]:
        """
        Calculate option price using Monte Carlo simulation from Black-Scholes SDE:
        dS = r * S * dt + sigma * S * dW
        """
        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return None

        payoffs: List[float] = []
        for _ in range(n_paths):
            # Simulate end-of-period price
            z = random.gauss(0, 1)
            ST = S * math.exp((r - 0.5 * sigma**2) * T + sigma * math.sqrt(T) * z)
            if option_type.lower() == "call":
                payoff = max(ST - K, 0)
            else:
                payoff = max(K - ST, 0)
            payoffs.append(payoff)

        discounted_payoff = math.exp(-r * T) * sum(payoffs) / n_paths
        return discounted_payoff

    def calculate_price_pde(
        self,
        S: float,
        K: float,
        r: float,
        sigma: float,
        T: float,
        option_type: str = "call",
        S_max: Optional[float] = None,
        M: int = 100,      # price steps
        N: int = 100,      # time steps
    ) -> Optional[float]:
        """
        Calculate option price using finite difference method (explicit) from Black-Scholes PDE:
        ∂V/∂t + 0.5*sigma^2*S^2*∂²V/∂S² + r*S*∂V/∂S - r*V = 0
        """
        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return None

        S_max = S_max or 2 * K
        dt = T / N
        dS = S_max / M

        # Initialize asset prices and option values
        grid = [[0.0 for _ in range(M + 1)] for _ in range(N + 1)]
        S_values = [i * dS for i in range(M + 1)]

        # Terminal condition
        for i in range(M + 1):
            if option_type.lower() == "call":
                grid[N][i] = max(S_values[i] - K, 0)
            else:
                grid[N][i] = max(K - S_values[i], 0)

        # Backward induction
        for j in reversed(range(N)):
            for i in range(1, M):
                delta = (grid[j + 1][i + 1] - grid[j + 1][i - 1]) / (2 * dS)
                gamma = (grid[j + 1][i + 1] - 2 * grid[j + 1][i] + grid[j + 1][i - 1]) / (dS ** 2)
                grid[j][i] = grid[j + 1][i] + dt * (0.5 * sigma**2 * S_values[i]**2 * gamma + r * S_values[i] * delta - r * grid[j + 1][i])

            # Boundary conditions
            grid[j][0] = 0 if option_type.lower() == "call" else K * math.exp(-r * dt * (N - j))
            grid[j][M] = S_max - K * math.exp(-r * dt * (N - j)) if option_type.lower() == "call" else 0

        # Interpolate to find price at S
        i = int(S / dS)
        return grid[0][i]
