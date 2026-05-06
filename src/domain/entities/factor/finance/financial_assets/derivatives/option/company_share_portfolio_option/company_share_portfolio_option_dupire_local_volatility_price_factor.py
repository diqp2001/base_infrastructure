import math
import random
from typing import Optional, Callable
import numpy as np

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_factor import CompanySharePortfolioOptionFactor


class CompanySharePortfolioOptionDupireLocalVolatilityPriceFactor(CompanySharePortfolioOptionFactor):
    """Dupire Local Volatility price factor for portfolio company share options with multi-dimensional local volatility surface."""

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
        local_vol_func: Optional[Callable[[float, float], float]] = None,  # σ_LV(S,t)
        q: float = 0.0,    # portfolio dividend yield
        option_type: str = "call",
        n_paths: int = 50000,  # number of Monte Carlo paths
        n_steps: int = 252,    # number of time steps per year
        volatility_surface: Optional[dict] = None,  # market volatility surface
        multiplier: int = 100,  # contract multiplier
    ) -> Optional[float]:
        """
        Calculate portfolio option price using Dupire Local Volatility model via Monte Carlo.
        
        The local volatility model for portfolios assumes:
        dS = (r - q)*S*dt + σ_LV(S,t)*S*dW
        
        Where σ_LV(S,t) is the local volatility function derived from market prices
        using Dupire's formula for the portfolio as a whole.
        """
        if S <= 0 or K <= 0 or T <= 0:
            return None

        try:
            # If no local volatility function provided, use a simple parameterization
            if local_vol_func is None:
                local_vol_func = self._default_portfolio_local_vol_function

            dt = T / n_steps
            sqrt_dt = math.sqrt(dt)
            
            payoffs = []
            
            for _ in range(n_paths):
                S_t = S
                
                for i in range(n_steps):
                    t = i * dt
                    
                    # Get local volatility at current (S,t)
                    local_vol = local_vol_func(S_t, t)
                    if local_vol <= 0:
                        local_vol = 0.01  # Small positive value to avoid issues
                    
                    # Generate random number
                    z = random.gauss(0, 1)
                    
                    # Update portfolio price using Euler-Maruyama scheme
                    dS = (r - q) * S_t * dt + local_vol * S_t * sqrt_dt * z
                    S_t += dS
                    S_t = max(S_t, 0)  # Ensure price remains positive
                
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

    def calculate_basket_option(
        self,
        spot_prices: list,     # [S1, S2, ..., Sn] individual asset prices
        weights: list,         # [w1, w2, ..., wn] portfolio weights
        K: float,              # strike price
        r: float,              # risk-free rate
        T: float,              # time to maturity
        correlations: list,    # correlation matrix for assets
        volatilities: list,    # [σ1, σ2, ..., σn] individual volatilities
        local_vol_surfaces: list = None,  # individual local vol surfaces for each asset
        basket_local_vol_func: Optional[Callable[[list, float], list]] = None,  # multi-dimensional local vol
        dividend_yields: list = None,  # [q1, q2, ..., qn] individual dividend yields
        option_type: str = "call",
        n_paths: int = 25000,  # reduced due to complexity
        n_steps: int = 126,    # reduced for computational efficiency
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate basket/portfolio option price using multi-dimensional local volatility.
        
        Each asset can have its own local volatility surface, and the basket volatility
        is determined by the interaction of individual local volatilities with correlations.
        """
        if not spot_prices or not weights or not volatilities:
            return None
        
        n_assets = len(spot_prices)
        if len(weights) != n_assets or len(volatilities) != n_assets:
            return None

        try:
            # Set default dividend yields if not provided
            if dividend_yields is None:
                dividend_yields = [0.0] * n_assets

            # Set default local volatility surfaces if not provided
            if local_vol_surfaces is None:
                local_vol_surfaces = [self._default_asset_local_vol_function] * n_assets

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

            # Cholesky decomposition for correlation
            try:
                L = np.linalg.cholesky(corr_matrix)
            except np.linalg.LinAlgError:
                # Fall back to simplified calculation
                return self._simplified_basket_local_vol(
                    spot_prices, weights, K, r, T, volatilities,
                    dividend_yields, option_type, n_paths, n_steps, multiplier
                )
            
            payoffs = []
            
            for _ in range(n_paths):
                current_prices = spot_prices.copy()
                
                for step in range(n_steps):
                    t = step * dt
                    
                    # Generate correlated random numbers
                    z = np.random.standard_normal(n_assets)
                    corr_z = L @ z
                    
                    # Calculate local volatilities for each asset
                    local_vols = []
                    for i in range(n_assets):
                        if callable(local_vol_surfaces[i]):
                            local_vol = local_vol_surfaces[i](current_prices[i], t)
                        else:
                            # Use default if not callable
                            local_vol = self._default_asset_local_vol_function(current_prices[i], t)
                        local_vols.append(max(local_vol, 0.01))
                    
                    # Update each asset price
                    for i in range(n_assets):
                        drift = (r - dividend_yields[i]) * dt
                        diffusion = local_vols[i] * sqrt_dt * corr_z[i]
                        
                        current_prices[i] *= math.exp(drift - 0.5 * local_vols[i]**2 * dt + diffusion)
                        current_prices[i] = max(current_prices[i], 0)
                
                # Calculate portfolio value
                portfolio_value = sum(w * S for w, S in zip(weights, current_prices))
                
                # Calculate payoff
                if option_type.lower() == "call":
                    payoff = max(portfolio_value - K, 0)
                else:  # put
                    payoff = max(K - portfolio_value, 0)
                
                payoffs.append(payoff)
            
            # Discount the expected payoff
            option_price = math.exp(-r * T) * sum(payoffs) / len(payoffs)
            return option_price * multiplier

        except (ValueError, ZeroDivisionError, OverflowError, np.linalg.LinAlgError):
            return None

    def _simplified_basket_local_vol(
        self,
        spot_prices: list,
        weights: list,
        K: float,
        r: float,
        T: float,
        volatilities: list,
        dividend_yields: list,
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
            
            # Create portfolio local volatility function
            def portfolio_local_vol_func(S_port: float, t: float) -> float:
                # Simple approach: use value-weighted volatilities
                total_value = sum(w * S for w, S in zip(weights, spot_prices))
                value_weights = [w * S / total_value for w, S in zip(weights, spot_prices)]
                
                # Portfolio local vol as weighted average with level dependence
                base_vol = sum(vw * vol for vw, vol in zip(value_weights, volatilities))
                level_adjustment = pow(S_port / portfolio_value, -0.1)  # Mild level dependence
                time_adjustment = math.exp(-0.1 * t)  # Mild time decay
                
                return base_vol * level_adjustment * time_adjustment
            
            # Use single-asset approach with portfolio parameters
            return self.calculate(
                S=portfolio_value,
                K=K,
                r=r,
                T=T,
                local_vol_func=portfolio_local_vol_func,
                q=portfolio_dividend_yield,
                option_type=option_type,
                n_paths=n_paths,
                n_steps=n_steps,
                multiplier=multiplier
            )

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def _default_portfolio_local_vol_function(self, S: float, t: float) -> float:
        """
        Default local volatility function for portfolios with level and time dependence.
        """
        # Portfolio-specific CEV-like local volatility with time decay
        sigma_0 = 0.2  # Base volatility
        S_0 = 100      # Reference portfolio value
        beta = 0.8     # CEV exponent (less negative skew than individual stocks)
        time_decay = 0.05  # Time decay factor
        
        level_factor = pow(S / S_0, beta - 1)
        time_factor = math.exp(-time_decay * t)
        
        return sigma_0 * level_factor * time_factor

    def _default_asset_local_vol_function(self, S: float, t: float) -> float:
        """
        Default local volatility function for individual assets in the basket.
        """
        # Individual asset CEV-like local volatility
        sigma_0 = 0.25  # Base volatility (higher than portfolio)
        S_0 = 50        # Reference asset price
        beta = 0.7      # CEV exponent (more negative skew)
        
        return sigma_0 * pow(S / S_0, beta - 1)

    def _norm_cdf(self, x: float) -> float:
        """Standard normal cumulative distribution function."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def _norm_pdf(self, x: float) -> float:
        """Standard normal probability density function."""
        return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)