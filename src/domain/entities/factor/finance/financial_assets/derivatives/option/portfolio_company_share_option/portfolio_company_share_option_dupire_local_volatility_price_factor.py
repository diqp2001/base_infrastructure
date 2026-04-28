import math
import random
from typing import Optional, Callable
import numpy as np

from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_factor import PortfolioCompanyShareOptionFactor


class PortfolioCompanyShareOptionDupireLocalVolatilityPriceFactor(PortfolioCompanyShareOptionFactor):
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

    def calibrate_basket_local_volatility_surface(
        self,
        market_prices: dict,  # {(asset_index, K, T): market_price}
        spot_prices: list,
        weights: list,
        r: float,
        q: float = 0.0,
        correlations: list = None,
    ) -> Optional[dict]:
        """
        Calibrate local volatility surfaces for basket options from market option prices.
        
        This is a complex procedure that requires market data for options on individual
        assets as well as basket options.
        """
        try:
            if not market_prices:
                return None

            n_assets = len(spot_prices)
            
            # Separate individual asset options from basket options
            individual_options = {}
            basket_options = {}
            
            for (asset_idx, K, T), price in market_prices.items():
                if asset_idx < n_assets:
                    # Individual asset option
                    if asset_idx not in individual_options:
                        individual_options[asset_idx] = {}
                    individual_options[asset_idx][(K, T)] = price
                else:
                    # Basket option (asset_idx = -1 or special value)
                    basket_options[(K, T)] = price

            # Calibrate individual local volatility surfaces
            individual_local_vol_functions = []
            
            for i in range(n_assets):
                if i in individual_options:
                    local_vol_func = self._calibrate_individual_local_vol(
                        individual_options[i], spot_prices[i], r, q
                    )
                    individual_local_vol_functions.append(local_vol_func)
                else:
                    # Use default if no market data
                    individual_local_vol_functions.append(self._default_asset_local_vol_function)

            # Calibrate basket local volatility (simplified approach)
            basket_local_vol_func = None
            if basket_options:
                portfolio_value = sum(w * S for w, S in zip(weights, spot_prices))
                basket_local_vol_func = self._calibrate_basket_local_vol(
                    basket_options, portfolio_value, r, q
                )

            return {
                "individual_local_vol_functions": individual_local_vol_functions,
                "basket_local_vol_function": basket_local_vol_func,
                "calibration_quality": self._assess_calibration_quality(market_prices)
            }

        except Exception:
            return None

    def _calibrate_individual_local_vol(
        self,
        asset_market_prices: dict,  # {(K, T): price}
        S0: float,
        r: float,
        q: float,
    ) -> Optional[Callable[[float, float], float]]:
        """Calibrate local volatility for a single asset."""
        try:
            # Convert to implied volatilities
            implied_vols = {}
            for (K, T), price in asset_market_prices.items():
                impl_vol = self._implied_volatility_from_price(price, S0, K, r, T, q)
                if impl_vol is not None:
                    implied_vols[(K, T)] = impl_vol

            if not implied_vols:
                return None

            def local_vol_function(S: float, t: float) -> float:
                try:
                    # Use current spot as strike for local volatility calculation
                    K = S
                    T_remaining = max(t, 1e-6)
                    
                    # Interpolate implied volatility
                    sigma = self._interpolate_implied_vol(implied_vols, K, T_remaining)
                    
                    # Simplified Dupire conversion
                    return max(sigma * (1 + 0.1 * math.log(S / S0)), 0.01)

                except (ValueError, ZeroDivisionError, OverflowError):
                    return 0.2  # Default

            return local_vol_function

        except Exception:
            return None

    def _calibrate_basket_local_vol(
        self,
        basket_market_prices: dict,  # {(K, T): price}
        portfolio_value: float,
        r: float,
        q: float,
    ) -> Optional[Callable[[float, float], float]]:
        """Calibrate local volatility for the basket."""
        try:
            # Similar to individual calibration but for basket
            implied_vols = {}
            for (K, T), price in basket_market_prices.items():
                impl_vol = self._implied_volatility_from_price(price, portfolio_value, K, r, T, q)
                if impl_vol is not None:
                    implied_vols[(K, T)] = impl_vol

            if not implied_vols:
                return None

            def basket_local_vol_function(S: float, t: float) -> float:
                try:
                    K = S
                    T_remaining = max(t, 1e-6)
                    
                    sigma = self._interpolate_implied_vol(implied_vols, K, T_remaining)
                    
                    # Portfolio-specific adjustments
                    level_adj = pow(S / portfolio_value, -0.1)
                    return max(sigma * level_adj, 0.01)

                except (ValueError, ZeroDivisionError, OverflowError):
                    return 0.2

            return basket_local_vol_function

        except Exception:
            return None

    def _interpolate_implied_vol(self, implied_vols: dict, K: float, T: float) -> float:
        """Simple interpolation of implied volatility surface."""
        if not implied_vols:
            return 0.2

        # Find nearest neighbors
        min_dist = float('inf')
        best_vol = 0.2

        for (K_market, T_market), vol in implied_vols.items():
            dist = math.sqrt((K - K_market)**2 + (T - T_market)**2)
            if dist < min_dist:
                min_dist = dist
                best_vol = vol

        return best_vol

    def _assess_calibration_quality(self, market_prices: dict) -> dict:
        """Assess the quality of the calibration."""
        return {
            "num_market_prices": len(market_prices),
            "calibration_method": "simplified_dupire",
            "quality_score": min(1.0, len(market_prices) / 50)  # Simple scoring
        }

    def calculate_pde_solution_basket(
        self,
        spot_prices: list,
        weights: list,
        K: float,
        r: float,
        T: float,
        local_vol_surfaces: list,
        correlations: list,
        dividend_yields: list = None,
        option_type: str = "call",
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Solve the multi-dimensional local volatility PDE for basket options.
        
        Note: This is computationally very intensive and typically requires
        specialized numerical methods. This implementation provides a simplified
        Monte Carlo approximation.
        """
        # Due to computational complexity, fall back to Monte Carlo
        return self.calculate_basket_option(
            spot_prices=spot_prices,
            weights=weights,
            K=K,
            r=r,
            T=T,
            correlations=correlations,
            volatilities=[0.2] * len(spot_prices),  # Default if not provided
            local_vol_surfaces=local_vol_surfaces,
            dividend_yields=dividend_yields,
            option_type=option_type,
            n_paths=50000,
            n_steps=252,
            multiplier=multiplier
        )

    def _implied_volatility_from_price(
        self,
        price: float,
        S: float,
        K: float,
        r: float,
        T: float,
        q: float = 0.0,
        option_type: str = "call",
    ) -> Optional[float]:
        """Calculate implied volatility from option price using Newton-Raphson method."""
        if price <= 0 or S <= 0 or K <= 0 or T <= 0:
            return None

        try:
            # Initial guess
            sigma = 0.2
            
            for _ in range(100):  # Maximum iterations
                # Calculate Black-Scholes price and vega
                d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
                d2 = d1 - sigma * math.sqrt(T)
                
                if option_type.lower() == "call":
                    bs_price = S * math.exp(-q * T) * self._norm_cdf(d1) - K * math.exp(-r * T) * self._norm_cdf(d2)
                else:  # put
                    bs_price = K * math.exp(-r * T) * self._norm_cdf(-d2) - S * math.exp(-q * T) * self._norm_cdf(-d1)
                
                # Vega
                vega = S * math.exp(-q * T) * self._norm_pdf(d1) * math.sqrt(T)
                
                if abs(vega) < 1e-10:
                    break
                
                # Newton-Raphson update
                diff = bs_price - price
                if abs(diff) < 1e-8:
                    break
                
                sigma_new = sigma - diff / vega
                sigma = max(sigma_new, 1e-6)  # Keep positive
                
                if abs(sigma_new - sigma) < 1e-8:
                    break

            return sigma if sigma > 1e-6 else None

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def calculate_portfolio_greeks(
        self,
        spot_prices: list,
        weights: list,
        K: float,
        r: float,
        T: float,
        correlations: list,
        local_vol_surfaces: list,
        dividend_yields: list = None,
        option_type: str = "call",
        multiplier: int = 100,
    ) -> dict:
        """Calculate Greeks for basket option under local volatility model."""
        if not spot_prices or not weights:
            return {}

        try:
            # Calculate base price
            base_price = self.calculate_basket_option(
                spot_prices, weights, K, r, T, correlations,
                [0.2] * len(spot_prices),  # Default volatilities
                local_vol_surfaces, None, dividend_yields, option_type,
                10000, 63, multiplier  # Reduced for Greeks calculation
            )
            
            if base_price is None:
                return {}

            # Calculate individual deltas
            individual_deltas = []
            dS = 0.01  # 1% shift
            
            for i in range(min(len(spot_prices), 3)):  # Limit for computational efficiency
                spot_prices_up = spot_prices.copy()
                spot_prices_up[i] *= (1 + dS)
                
                price_up = self.calculate_basket_option(
                    spot_prices_up, weights, K, r, T, correlations,
                    [0.2] * len(spot_prices), local_vol_surfaces, None,
                    dividend_yields, option_type, 5000, 32, multiplier
                )
                
                if price_up is not None:
                    delta_i = (price_up - base_price) / (spot_prices[i] * dS)
                    individual_deltas.append(delta_i)
                else:
                    individual_deltas.append(0.0)

            return {
                "individual_deltas": individual_deltas,
                "total_delta": sum(individual_deltas),
                "base_price": base_price,
                "note": "Greeks calculated with reduced precision due to model complexity"
            }

        except (ValueError, ZeroDivisionError, OverflowError):
            return {}

    def _norm_cdf(self, x: float) -> float:
        """Standard normal cumulative distribution function."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def _norm_pdf(self, x: float) -> float:
        """Standard normal probability density function."""
        return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)