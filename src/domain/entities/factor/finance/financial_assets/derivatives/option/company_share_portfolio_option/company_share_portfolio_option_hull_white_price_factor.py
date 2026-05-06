import math
import random
from typing import Optional
import numpy as np

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_factor import CompanySharePortfolioOptionFactor


class CompanySharePortfolioOptionHullWhitePriceFactor(CompanySharePortfolioOptionFactor):
    """Hull-White stochastic interest rate price factor for portfolio company share options with multiple asset support."""

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
        r0: float,         # initial interest rate
        T: float,          # time to maturity in years
        sigma: float,      # portfolio volatility
        a: float,          # mean reversion speed for interest rate
        sigma_r: float,    # interest rate volatility
        rho: float,        # correlation between portfolio and interest rate
        q: float = 0.0,    # portfolio dividend yield
        option_type: str = "call",
        n_paths: int = 50000,  # number of Monte Carlo paths
        n_steps: int = 252,    # number of time steps per year
        multiplier: int = 100,  # contract multiplier
    ) -> Optional[float]:
        """
        Calculate portfolio option price using Hull-White stochastic interest rate model via Monte Carlo.
        
        The Hull-White model for portfolios assumes:
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
                    
                    # Update portfolio price
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
            return option_price * multiplier

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def calculate_basket_option(
        self,
        spot_prices: list,     # [S1, S2, ..., Sn] individual asset prices
        weights: list,         # [w1, w2, ..., wn] portfolio weights
        K: float,              # strike price
        r0: float,             # initial interest rate
        T: float,              # time to maturity
        correlations: list,    # correlation matrix for assets
        volatilities: list,    # [σ1, σ2, ..., σn] individual volatilities
        asset_rate_correlations: list,  # correlations between each asset and interest rate
        a: float,              # mean reversion speed for interest rate
        sigma_r: float,        # interest rate volatility
        dividend_yields: list = None,  # [q1, q2, ..., qn] individual dividend yields
        option_type: str = "call",
        n_paths: int = 50000,
        n_steps: int = 252,
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate basket/portfolio option price with stochastic interest rates affecting multiple assets.
        
        Each asset in the portfolio can have different correlation with the interest rate,
        allowing for more realistic modeling of interest rate sensitivity across assets.
        """
        if not spot_prices or not weights or not volatilities:
            return None
        
        n_assets = len(spot_prices)
        if (len(weights) != n_assets or len(volatilities) != n_assets or
            len(asset_rate_correlations) != n_assets):
            return None

        try:
            # Set default dividend yields if not provided
            if dividend_yields is None:
                dividend_yields = [0.0] * n_assets

            dt = T / n_steps
            sqrt_dt = math.sqrt(dt)
            
            # Handle correlation matrix
            if isinstance(correlations[0], list):
                corr_matrix = np.array(correlations)
            else:
                # Convert flat to 2D
                corr_matrix = np.eye(n_assets)
                idx = 0
                for i in range(n_assets):
                    for j in range(i + 1, n_assets):
                        corr_matrix[i, j] = correlations[idx]
                        corr_matrix[j, i] = correlations[idx]
                        idx += 1

            # Extend correlation matrix to include interest rate
            extended_corr = np.zeros((n_assets + 1, n_assets + 1))
            extended_corr[:n_assets, :n_assets] = corr_matrix
            extended_corr[n_assets, n_assets] = 1.0  # interest rate with itself
            
            # Set correlations between assets and interest rate
            for i in range(n_assets):
                extended_corr[i, n_assets] = asset_rate_correlations[i]
                extended_corr[n_assets, i] = asset_rate_correlations[i]

            # Cholesky decomposition for correlation
            try:
                L = np.linalg.cholesky(extended_corr)
            except np.linalg.LinAlgError:
                # If correlation matrix is not positive definite, use simplified approach
                return self._simplified_basket_calculation(
                    spot_prices, weights, K, r0, T, volatilities, dividend_yields,
                    a, sigma_r, option_type, n_paths, n_steps, multiplier
                )
            
            payoffs = []
            
            for _ in range(n_paths):
                current_prices = spot_prices.copy()
                r_t = r0
                
                for _ in range(n_steps):
                    # Generate correlated random numbers for all assets + interest rate
                    z = np.random.standard_normal(n_assets + 1)
                    corr_z = L @ z
                    
                    # For simplicity, assume theta(t) = r0
                    theta_t = r0
                    
                    # Update interest rate
                    dr = a * (theta_t - r_t) * dt + sigma_r * sqrt_dt * corr_z[n_assets]
                    r_t += dr
                    
                    # Update each asset price
                    for i in range(n_assets):
                        drift = (r_t - dividend_yields[i]) * dt
                        diffusion = volatilities[i] * sqrt_dt * corr_z[i]
                        current_prices[i] *= math.exp(drift - 0.5 * volatilities[i]**2 * dt + diffusion)
                        current_prices[i] = max(current_prices[i], 0)
                
                # Calculate portfolio value
                portfolio_value = sum(w * S for w, S in zip(weights, current_prices))
                
                # Calculate payoff
                if option_type.lower() == "call":
                    payoff = max(portfolio_value - K, 0)
                else:  # put
                    payoff = max(K - portfolio_value, 0)
                
                payoffs.append(payoff)
            
            # Discount using average interest rate path
            avg_r = sum(self._get_avg_rate_path(r0, a, sigma_r, T, n_steps) for _ in range(1000)) / 1000
            option_price = math.exp(-avg_r * T) * sum(payoffs) / len(payoffs)
            return option_price * multiplier

        except (ValueError, ZeroDivisionError, OverflowError, np.linalg.LinAlgError):
            return None

    def _simplified_basket_calculation(
        self,
        spot_prices: list,
        weights: list,
        K: float,
        r0: float,
        T: float,
        volatilities: list,
        dividend_yields: list,
        a: float,
        sigma_r: float,
        option_type: str,
        n_paths: int,
        n_steps: int,
        multiplier: int,
    ) -> Optional[float]:
        """Simplified calculation when correlation matrix is problematic."""
        try:
            # Calculate portfolio parameters
            portfolio_value = sum(w * S for w, S in zip(weights, spot_prices))
            portfolio_dividend_yield = sum(w * S * q for w, S, q in zip(weights, spot_prices, dividend_yields)) / portfolio_value
            
            # Portfolio volatility (assuming zero correlation for simplicity)
            portfolio_variance = sum((w * S / portfolio_value * vol)**2 for w, S, vol in zip(weights, spot_prices, volatilities))
            portfolio_volatility = math.sqrt(portfolio_variance)
            
            # Use single-asset approach with portfolio parameters
            return self.calculate(
                S=portfolio_value,
                K=K,
                r0=r0,
                T=T,
                sigma=portfolio_volatility,
                a=a,
                sigma_r=sigma_r,
                rho=0.1,  # Default correlation
                q=portfolio_dividend_yield,
                option_type=option_type,
                n_paths=n_paths,
                n_steps=n_steps,
                multiplier=multiplier
            )

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

    def _norm_cdf(self, x: float) -> float:
        """Standard normal cumulative distribution function."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))