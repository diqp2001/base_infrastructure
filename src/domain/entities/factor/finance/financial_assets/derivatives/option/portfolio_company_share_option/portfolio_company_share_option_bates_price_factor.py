import math
import random
from typing import Optional
import numpy as np

from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_factor import PortfolioCompanyShareOptionFactor


class PortfolioCompanyShareOptionBatesPriceFactor(PortfolioCompanyShareOptionFactor):
    """Bates model (Heston with jump diffusion) price factor for portfolio company share options with correlation and jumps."""

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
        rho: float,        # correlation between asset and volatility
        lambda_j: float,   # jump intensity (jumps per year)
        mu_j: float,       # mean jump size (log scale)
        sigma_j: float,    # jump volatility
        q: float = 0.0,    # portfolio dividend yield
        option_type: str = "call",
        n_paths: int = 50000,  # number of Monte Carlo paths
        n_steps: int = 252,    # number of time steps per year
        multiplier: int = 100,  # contract multiplier
    ) -> Optional[float]:
        """
        Calculate portfolio option price using Bates model (Heston + jump diffusion) via Monte Carlo.
        
        The Bates model for portfolios extends Heston with jumps:
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
                    
                    # Update portfolio price with diffusion and jumps
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
        v0_individual: list,   # initial volatility squared for each asset
        kappa_individual: list, # mean reversion speeds
        theta_individual: list, # long-term volatilities
        xi_individual: list,   # volatility of volatilities
        rho_individual: list,  # correlations between each asset and its volatility
        lambda_j_individual: list, # jump intensities for each asset
        mu_j_individual: list, # mean jump sizes
        sigma_j_individual: list, # jump volatilities
        jump_correlations: list = None, # correlation matrix for jumps
        dividend_yields: list = None,  # [q1, q2, ..., qn] individual dividend yields
        option_type: str = "call",
        n_paths: int = 25000,  # reduced due to complexity
        n_steps: int = 126,    # reduced for computational efficiency
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate basket/portfolio option price using multi-dimensional Bates model.
        
        Each asset in the portfolio follows its own Bates process with:
        - Individual stochastic volatility parameters
        - Individual jump process parameters
        - Correlation structure between assets
        - Potential correlation between jump processes
        """
        if not spot_prices or not weights or not volatilities:
            return None
        
        n_assets = len(spot_prices)
        required_lists = [weights, volatilities, v0_individual, kappa_individual, 
                         theta_individual, xi_individual, rho_individual,
                         lambda_j_individual, mu_j_individual, sigma_j_individual]
        
        if any(len(lst) != n_assets for lst in required_lists):
            return None

        try:
            # Set default dividend yields if not provided
            if dividend_yields is None:
                dividend_yields = [0.0] * n_assets

            # Set default jump correlations (independent jumps)
            if jump_correlations is None:
                jump_correlations = np.eye(n_assets).tolist()

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

            # Extend correlation matrix to include volatility processes
            # Structure: [S1, S2, ..., Sn, v1, v2, ..., vn]
            extended_size = 2 * n_assets
            extended_corr = np.eye(extended_size)
            
            # Asset-asset correlations
            extended_corr[:n_assets, :n_assets] = corr_matrix
            
            # Asset-volatility correlations (diagonal only for simplicity)
            for i in range(n_assets):
                extended_corr[i, n_assets + i] = rho_individual[i]
                extended_corr[n_assets + i, i] = rho_individual[i]

            # Cholesky decomposition for correlation
            try:
                L = np.linalg.cholesky(extended_corr)
            except np.linalg.LinAlgError:
                # Fall back to simplified calculation
                return self._simplified_basket_bates(
                    spot_prices, weights, K, r, T, volatilities, v0_individual,
                    kappa_individual, theta_individual, xi_individual, rho_individual,
                    lambda_j_individual, mu_j_individual, sigma_j_individual,
                    dividend_yields, option_type, n_paths, n_steps, multiplier
                )
            
            # Calculate jump compensation terms for each asset
            k_values = [math.exp(mu_j + 0.5 * sigma_j * sigma_j) - 1 
                       for mu_j, sigma_j in zip(mu_j_individual, sigma_j_individual)]
            
            payoffs = []
            
            for _ in range(n_paths):
                current_prices = spot_prices.copy()
                current_vols = v0_individual.copy()
                
                for _ in range(n_steps):
                    # Generate correlated random numbers for all processes
                    z = np.random.standard_normal(extended_size)
                    corr_z = L @ z
                    
                    # Update each asset
                    for i in range(n_assets):
                        # Ensure volatility remains positive
                        current_vols[i] = max(current_vols[i], 0)
                        sqrt_v = math.sqrt(current_vols[i]) if current_vols[i] > 0 else 0
                        
                        # Generate jumps for this asset
                        n_jumps = self._poisson_random(lambda_j_individual[i] * dt)
                        jump_component = 1.0
                        
                        for _ in range(n_jumps):
                            # Log-normal jump size
                            jump_log = random.gauss(mu_j_individual[i], sigma_j_individual[i])
                            jump_component *= (1 + (math.exp(jump_log) - 1))
                        
                        # Update asset price with diffusion and jumps
                        drift = (r - dividend_yields[i] - lambda_j_individual[i] * k_values[i]) * dt
                        diffusion = sqrt_v * sqrt_dt * corr_z[i]
                        
                        current_prices[i] *= math.exp(drift - 0.5 * current_vols[i] * dt + diffusion) * jump_component
                        current_prices[i] = max(current_prices[i], 0)
                        
                        # Update volatility process
                        dv = (kappa_individual[i] * (theta_individual[i] - current_vols[i]) * dt +
                              xi_individual[i] * sqrt_v * sqrt_dt * corr_z[n_assets + i])
                        current_vols[i] += dv
                        current_vols[i] = max(current_vols[i], 0)
                
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

    def _simplified_basket_bates(
        self,
        spot_prices: list,
        weights: list,
        K: float,
        r: float,
        T: float,
        volatilities: list,
        v0_individual: list,
        kappa_individual: list,
        theta_individual: list,
        xi_individual: list,
        rho_individual: list,
        lambda_j_individual: list,
        mu_j_individual: list,
        sigma_j_individual: list,
        dividend_yields: list,
        option_type: str,
        n_paths: int,
        n_steps: int,
        multiplier: int,
    ) -> Optional[float]:
        """Simplified Bates calculation when correlation matrix is problematic."""
        try:
            # Calculate portfolio parameters (weighted averages)
            portfolio_value = sum(w * S for w, S in zip(weights, spot_prices))
            
            # Portfolio-level parameters (value-weighted)
            total_weight = sum(w * S for w, S in zip(weights, spot_prices))
            value_weights = [w * S / total_weight for w, S in zip(weights, spot_prices)]
            
            portfolio_v0 = sum(vw * v0 for vw, v0 in zip(value_weights, v0_individual))
            portfolio_kappa = sum(vw * kappa for vw, kappa in zip(value_weights, kappa_individual))
            portfolio_theta = sum(vw * theta for vw, theta in zip(value_weights, theta_individual))
            portfolio_xi = sum(vw * xi for vw, xi in zip(value_weights, xi_individual))
            portfolio_rho = sum(vw * rho for vw, rho in zip(value_weights, rho_individual))
            portfolio_lambda_j = sum(vw * lambda_j for vw, lambda_j in zip(value_weights, lambda_j_individual))
            portfolio_mu_j = sum(vw * mu_j for vw, mu_j in zip(value_weights, mu_j_individual))
            portfolio_sigma_j = math.sqrt(sum(vw * sigma_j**2 for vw, sigma_j in zip(value_weights, sigma_j_individual)))
            portfolio_dividend_yield = sum(vw * q for vw, q in zip(value_weights, dividend_yields))
            
            # Use single-asset Bates with portfolio parameters
            return self.calculate(
                S=portfolio_value,
                K=K,
                r=r,
                T=T,
                v0=portfolio_v0,
                kappa=portfolio_kappa,
                theta=portfolio_theta,
                xi=portfolio_xi,
                rho=portfolio_rho,
                lambda_j=portfolio_lambda_j,
                mu_j=portfolio_mu_j,
                sigma_j=portfolio_sigma_j,
                q=portfolio_dividend_yield,
                option_type=option_type,
                n_paths=n_paths,
                n_steps=n_steps,
                multiplier=multiplier
            )

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

    def calculate_common_jump_basket(
        self,
        spot_prices: list,
        weights: list,
        K: float,
        r: float,
        T: float,
        correlations: list,
        individual_params: dict,  # Contains all individual Bates parameters
        common_jump_intensity: float,  # Common jump intensity affecting all assets
        common_jump_mean: float,  # Common jump mean size
        common_jump_vol: float,   # Common jump volatility
        jump_betas: list,         # Sensitivity of each asset to common jumps
        dividend_yields: list = None,
        option_type: str = "call",
        n_paths: int = 25000,
        n_steps: int = 126,
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate portfolio option price with common jump factor affecting all assets.
        
        This models systematic risk where all assets can jump together during
        market stress events, in addition to their individual jump processes.
        """
        if not spot_prices or not weights or not jump_betas:
            return None

        n_assets = len(spot_prices)
        if len(weights) != n_assets or len(jump_betas) != n_assets:
            return None

        try:
            if dividend_yields is None:
                dividend_yields = [0.0] * n_assets

            dt = T / n_steps
            sqrt_dt = math.sqrt(dt)
            
            # Extract individual parameters
            v0_individual = individual_params.get('v0_individual', [0.04] * n_assets)
            kappa_individual = individual_params.get('kappa_individual', [2.0] * n_assets)
            theta_individual = individual_params.get('theta_individual', [0.04] * n_assets)
            xi_individual = individual_params.get('xi_individual', [0.3] * n_assets)
            rho_individual = individual_params.get('rho_individual', [-0.5] * n_assets)
            lambda_j_individual = individual_params.get('lambda_j_individual', [0.1] * n_assets)
            mu_j_individual = individual_params.get('mu_j_individual', [0.0] * n_assets)
            sigma_j_individual = individual_params.get('sigma_j_individual', [0.1] * n_assets)

            # Common jump compensation
            common_k = math.exp(common_jump_mean + 0.5 * common_jump_vol * common_jump_vol) - 1
            
            # Individual jump compensations
            k_values = [math.exp(mu_j + 0.5 * sigma_j * sigma_j) - 1 
                       for mu_j, sigma_j in zip(mu_j_individual, sigma_j_individual)]
            
            payoffs = []
            
            for _ in range(n_paths):
                current_prices = spot_prices.copy()
                current_vols = v0_individual.copy()
                
                for _ in range(n_steps):
                    # Generate common jump
                    n_common_jumps = self._poisson_random(common_jump_intensity * dt)
                    common_jump_factor = 0.0
                    
                    for _ in range(n_common_jumps):
                        common_jump_log = random.gauss(common_jump_mean, common_jump_vol)
                        common_jump_factor += common_jump_log
                    
                    # Update each asset
                    for i in range(n_assets):
                        # Ensure volatility remains positive
                        current_vols[i] = max(current_vols[i], 0)
                        sqrt_v = math.sqrt(current_vols[i]) if current_vols[i] > 0 else 0
                        
                        # Generate individual jumps
                        n_individual_jumps = self._poisson_random(lambda_j_individual[i] * dt)
                        individual_jump_component = 1.0
                        
                        for _ in range(n_individual_jumps):
                            jump_log = random.gauss(mu_j_individual[i], sigma_j_individual[i])
                            individual_jump_component *= (1 + (math.exp(jump_log) - 1))
                        
                        # Apply common jump with individual sensitivity
                        common_jump_component = math.exp(jump_betas[i] * common_jump_factor)
                        
                        # Generate correlated diffusion (simplified)
                        z1 = random.gauss(0, 1)
                        z2 = rho_individual[i] * z1 + math.sqrt(1 - rho_individual[i]**2) * random.gauss(0, 1)
                        
                        # Update asset price
                        drift = (r - dividend_yields[i] - 
                                lambda_j_individual[i] * k_values[i] - 
                                common_jump_intensity * jump_betas[i] * common_k) * dt
                        diffusion = sqrt_v * sqrt_dt * z1
                        
                        current_prices[i] *= (math.exp(drift - 0.5 * current_vols[i] * dt + diffusion) * 
                                            individual_jump_component * common_jump_component)
                        current_prices[i] = max(current_prices[i], 0)
                        
                        # Update volatility
                        dv = (kappa_individual[i] * (theta_individual[i] - current_vols[i]) * dt +
                              xi_individual[i] * sqrt_v * sqrt_dt * z2)
                        current_vols[i] += dv
                        current_vols[i] = max(current_vols[i], 0)
                
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

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def calculate_portfolio_jump_statistics(
        self,
        weights: list,
        spot_prices: list,
        lambda_j_individual: list,
        mu_j_individual: list,
        sigma_j_individual: list,
        jump_correlations: list = None,
    ) -> dict:
        """Calculate aggregate jump statistics for the portfolio."""
        if not weights or not spot_prices or not lambda_j_individual:
            return {}

        try:
            n_assets = len(weights)
            
            # Calculate value weights
            total_value = sum(w * S for w, S in zip(weights, spot_prices))
            value_weights = [w * S / total_value for w, S in zip(weights, spot_prices)]
            
            # Portfolio jump intensity (weighted average)
            portfolio_lambda = sum(vw * lambda_j for vw, lambda_j in zip(value_weights, lambda_j_individual))
            
            # Portfolio expected jump size
            portfolio_expected_jump = sum(vw * (math.exp(mu_j + 0.5 * sigma_j**2) - 1)
                                        for vw, mu_j, sigma_j in zip(value_weights, mu_j_individual, sigma_j_individual))
            
            # Portfolio jump variance (simplified - assumes independence if no correlation matrix)
            if jump_correlations is None:
                portfolio_jump_variance = sum(vw**2 * ((math.exp(sigma_j**2) - 1) * math.exp(2*mu_j + sigma_j**2))
                                            for vw, mu_j, sigma_j in zip(value_weights, mu_j_individual, sigma_j_individual))
            else:
                # More complex calculation with correlations would go here
                portfolio_jump_variance = sum(vw**2 * ((math.exp(sigma_j**2) - 1) * math.exp(2*mu_j + sigma_j**2))
                                            for vw, mu_j, sigma_j in zip(value_weights, mu_j_individual, sigma_j_individual))
            
            return {
                "portfolio_jump_intensity": portfolio_lambda,
                "portfolio_expected_jump_size": portfolio_expected_jump,
                "portfolio_jump_variance": portfolio_jump_variance,
                "portfolio_jump_volatility": math.sqrt(portfolio_jump_variance),
                "expected_jumps_per_year": portfolio_lambda,
                "jump_contribution_to_variance": portfolio_lambda * (portfolio_expected_jump**2 + portfolio_jump_variance)
            }

        except (ValueError, ZeroDivisionError, OverflowError):
            return {}

    def calculate_portfolio_greeks(
        self,
        spot_prices: list,
        weights: list,
        K: float,
        r: float,
        T: float,
        correlations: list,
        individual_params: dict,
        dividend_yields: list = None,
        option_type: str = "call",
        multiplier: int = 100,
    ) -> dict:
        """Calculate Greeks for portfolio option under Bates model."""
        if not spot_prices or not weights:
            return {}

        try:
            # Calculate base price using simplified approach
            base_price = self._simplified_basket_bates(
                spot_prices, weights, K, r, T,
                individual_params.get('volatilities', [0.2] * len(spot_prices)),
                individual_params.get('v0_individual', [0.04] * len(spot_prices)),
                individual_params.get('kappa_individual', [2.0] * len(spot_prices)),
                individual_params.get('theta_individual', [0.04] * len(spot_prices)),
                individual_params.get('xi_individual', [0.3] * len(spot_prices)),
                individual_params.get('rho_individual', [-0.5] * len(spot_prices)),
                individual_params.get('lambda_j_individual', [0.1] * len(spot_prices)),
                individual_params.get('mu_j_individual', [0.0] * len(spot_prices)),
                individual_params.get('sigma_j_individual', [0.1] * len(spot_prices)),
                dividend_yields or [0.0] * len(spot_prices),
                option_type, 10000, 63, multiplier
            )
            
            if base_price is None:
                return {}

            # Calculate individual deltas (computationally intensive, so simplified)
            individual_deltas = []
            dS = 0.01  # 1% shift
            
            for i in range(min(len(spot_prices), 3)):  # Limit for computational efficiency
                spot_prices_up = spot_prices.copy()
                spot_prices_up[i] *= (1 + dS)
                
                price_up = self._simplified_basket_bates(
                    spot_prices_up, weights, K, r, T,
                    individual_params.get('volatilities', [0.2] * len(spot_prices)),
                    individual_params.get('v0_individual', [0.04] * len(spot_prices)),
                    individual_params.get('kappa_individual', [2.0] * len(spot_prices)),
                    individual_params.get('theta_individual', [0.04] * len(spot_prices)),
                    individual_params.get('xi_individual', [0.3] * len(spot_prices)),
                    individual_params.get('rho_individual', [-0.5] * len(spot_prices)),
                    individual_params.get('lambda_j_individual', [0.1] * len(spot_prices)),
                    individual_params.get('mu_j_individual', [0.0] * len(spot_prices)),
                    individual_params.get('sigma_j_individual', [0.1] * len(spot_prices)),
                    dividend_yields or [0.0] * len(spot_prices),
                    option_type, 5000, 32, multiplier
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
                "note": "Greeks calculated using simplified approach due to model complexity"
            }

        except (ValueError, ZeroDivisionError, OverflowError):
            return {}