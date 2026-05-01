import math
import random
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_factor import PortfolioCompanyShareOptionFactor


class PortfolioCompanyShareOptionSABRPriceFactor(PortfolioCompanyShareOptionFactor):
    """SABR (Stochastic Alpha Beta Rho) price factor for portfolio company share options."""

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
        F: float,          # forward portfolio price/level
        K: float,          # strike price
        T: float,          # time to maturity in years
        alpha: float,      # initial volatility
        beta: float,       # CEV exponent (0 <= beta <= 1)
        rho: float,        # correlation between forward and volatility
        nu: float,         # volatility of volatility
        r: float = 0.0,    # risk-free rate for discounting
        option_type: str = "call",
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate portfolio option price using SABR model via implied volatility approach.
        
        For portfolio options, F represents the forward portfolio value/index level.
        
        The SABR model assumes:
        dF = alpha * F^beta * dW1
        dalpha = nu * alpha * dW2
        
        Where dW1 and dW2 have correlation rho.
        """
        if F <= 0 or K <= 0 or T <= 0 or alpha <= 0 or beta < 0 or beta > 1:
            return None
        if abs(rho) >= 1 or nu < 0:
            return None

        try:
            # Calculate SABR implied volatility
            sabr_vol = self._sabr_implied_volatility(F, K, T, alpha, beta, rho, nu)
            if sabr_vol is None or sabr_vol <= 0:
                return None

            # Use Black-Scholes formula with SABR implied volatility
            d1 = (math.log(F / K) + 0.5 * sabr_vol ** 2 * T) / (sabr_vol * math.sqrt(T))
            d2 = d1 - sabr_vol * math.sqrt(T)

            if option_type.lower() == "call":
                price = math.exp(-r * T) * (F * self._norm_cdf(d1) - K * self._norm_cdf(d2))
            else:  # put
                price = math.exp(-r * T) * (K * self._norm_cdf(-d2) - F * self._norm_cdf(-d1))

            return price * multiplier

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def calculate_multi_asset_sabr(
        self,
        forwards: list,        # [F1, F2, ..., Fn] individual forward prices
        weights: list,         # [w1, w2, ..., wn] portfolio weights
        K: float,              # strike price
        T: float,              # time to maturity
        alphas: list,          # [α1, α2, ..., αn] initial volatilities
        betas: list,           # [β1, β2, ..., βn] CEV exponents
        correlations: list,    # correlation matrix between forwards and volatilities
        nus: list,             # [ν1, ν2, ..., νn] volatilities of volatilities
        r: float = 0.0,        # risk-free rate
        option_type: str = "call",
        multiplier: int = 100,
        n_paths: int = 50000,
        n_steps: int = 252,
    ) -> Optional[float]:
        """
        Calculate multi-asset portfolio option price with individual SABR processes.
        
        Each asset follows its own SABR process, combined into a portfolio option.
        """
        n_assets = len(forwards)
        if (len(weights) != n_assets or len(alphas) != n_assets or 
            len(betas) != n_assets or len(nus) != n_assets):
            return None

        try:
            dt = T / n_steps
            sqrt_dt = math.sqrt(dt)
            
            payoffs = []
            
            for _ in range(n_paths):
                F_t = forwards.copy()
                alpha_t = alphas.copy()
                
                for _ in range(n_steps):
                    # Generate correlated random numbers (simplified)
                    z = [random.gauss(0, 1) for _ in range(2 * n_assets)]
                    
                    # Update each asset's forward and volatility
                    for i in range(n_assets):
                        # Ensure positive values
                        F_t[i] = max(F_t[i], 1e-8)
                        alpha_t[i] = max(alpha_t[i], 1e-8)
                        
                        # Update forward price using SABR dynamics
                        dF = alpha_t[i] * (F_t[i] ** betas[i]) * sqrt_dt * z[i]
                        F_t[i] += dF
                        F_t[i] = max(F_t[i], 0)
                        
                        # Update volatility
                        dalpha = nus[i] * alpha_t[i] * sqrt_dt * z[i + n_assets]
                        alpha_t[i] += dalpha
                        alpha_t[i] = max(alpha_t[i], 1e-8)
                
                # Calculate portfolio forward value
                portfolio_forward = sum(w * F for w, F in zip(weights, F_t))
                
                # Calculate payoff
                if option_type.lower() == "call":
                    payoff = max(portfolio_forward - K, 0)
                else:  # put
                    payoff = max(K - portfolio_forward, 0)
                
                payoffs.append(payoff)
            
            # Discount the expected payoff
            option_price = math.exp(-r * T) * sum(payoffs) / len(payoffs)
            return option_price * multiplier

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def _sabr_implied_volatility(
        self,
        F: float,
        K: float,
        T: float,
        alpha: float,
        beta: float,
        rho: float,
        nu: float,
    ) -> Optional[float]:
        """
        Calculate SABR implied volatility using Hagan's formula.
        """
        try:
            # Handle ATM case
            if abs(F - K) < 1e-8:
                return self._sabr_atm_volatility(F, T, alpha, beta, rho, nu)

            # Constants
            FK = F * K
            log_FK = math.log(F / K)
            
            # z parameter
            z = (nu / alpha) * (FK ** ((1 - beta) / 2)) * log_FK
            
            # x(z) function
            if abs(z) < 1e-8:
                x_z = 1.0
            else:
                sqrt_term = math.sqrt(1 - 2 * rho * z + z * z)
                x_z = math.log((sqrt_term + z - rho) / (1 - rho)) / z

            # First term
            term1 = alpha / ((FK ** ((1 - beta) / 2)) * (1 + ((1 - beta) ** 2 / 24) * (log_FK ** 2) + 
                           ((1 - beta) ** 4 / 1920) * (log_FK ** 4)))

            # Second term
            term2 = x_z

            # Third term (time adjustment)
            term3_1 = ((1 - beta) ** 2 / 24) * (alpha ** 2) / (FK ** (1 - beta))
            term3_2 = (rho * beta * nu * alpha / 4) / (FK ** ((1 - beta) / 2))
            term3_3 = ((2 - 3 * rho ** 2) / 24) * (nu ** 2)
            
            term3 = 1 + (term3_1 + term3_2 + term3_3) * T

            implied_vol = term1 * term2 * term3
            return implied_vol if implied_vol > 0 else None

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def _sabr_atm_volatility(self, F: float, T: float, alpha: float, beta: float, rho: float, nu: float) -> float:
        """Calculate SABR ATM implied volatility."""
        try:
            # First term
            term1 = alpha / (F ** (1 - beta))

            # Time adjustment
            term2_1 = ((1 - beta) ** 2 / 24) * (alpha ** 2) / (F ** (2 * (1 - beta)))
            term2_2 = (rho * beta * nu * alpha / 4) / (F ** (1 - beta))
            term2_3 = ((2 - 3 * rho ** 2) / 24) * (nu ** 2)
            
            term2 = 1 + (term2_1 + term2_2 + term2_3) * T

            return term1 * term2

        except (ValueError, ZeroDivisionError, OverflowError):
            return 0.0

    def calculate_portfolio_sabr_parameters(
        self,
        individual_forwards: list,
        individual_alphas: list,
        individual_betas: list,
        individual_nus: list,
        weights: list,
        correlations: list,
    ) -> dict:
        """
        Calculate equivalent SABR parameters for a portfolio given individual asset parameters.
        
        This is an approximation method for portfolio-level SABR parameters.
        """
        n_assets = len(individual_forwards)
        if (len(individual_alphas) != n_assets or len(individual_betas) != n_assets or 
            len(individual_nus) != n_assets or len(weights) != n_assets):
            return {}

        try:
            # Calculate portfolio forward
            portfolio_forward = sum(w * F for w, F in zip(weights, individual_forwards))
            
            # Weighted average beta
            portfolio_beta = sum(w * F * beta for w, F, beta in zip(weights, individual_forwards, individual_betas)) / portfolio_forward
            
            # Approximate portfolio alpha (simplified approach)
            portfolio_alpha = 0.0
            for i in range(n_assets):
                weight_i = weights[i] * individual_forwards[i] / portfolio_forward
                portfolio_alpha += weight_i * individual_alphas[i] * (individual_forwards[i] ** (1 - individual_betas[i]))
            
            portfolio_alpha *= (portfolio_forward ** (1 - portfolio_beta))
            
            # Approximate portfolio nu (simplified)
            portfolio_nu_squared = 0.0
            for i in range(n_assets):
                for j in range(n_assets):
                    weight_i = weights[i] * individual_forwards[i] / portfolio_forward
                    weight_j = weights[j] * individual_forwards[j] / portfolio_forward
                    
                    # Simplified correlation structure
                    if i < len(correlations) and j < len(correlations[0]):
                        corr_ij = correlations[i][j] if i != j else 1.0
                    else:
                        corr_ij = 0.5 if i != j else 1.0
                    
                    portfolio_nu_squared += weight_i * weight_j * individual_nus[i] * individual_nus[j] * corr_ij
            
            portfolio_nu = math.sqrt(max(portfolio_nu_squared, 0))
            
            # Approximate portfolio rho (simplified to average)
            portfolio_rho = sum(individual_nus) / len(individual_nus) if individual_nus else 0.0
            portfolio_rho = max(min(portfolio_rho, 0.99), -0.99)  # Keep within valid bounds

            return {
                "alpha": portfolio_alpha,
                "beta": portfolio_beta,
                "rho": portfolio_rho,
                "nu": portfolio_nu
            }

        except (ValueError, ZeroDivisionError, OverflowError):
            return {}

    def calibrate_to_volatility_smile(
        self,
        market_vols: list,      # market implied volatilities
        strikes: list,          # corresponding strike prices
        F: float,               # forward price
        T: float,               # time to maturity
        initial_guess: dict = None,
    ) -> dict:
        """
        Calibrate SABR parameters to market volatility smile for portfolio options.
        """
        if len(market_vols) != len(strikes) or len(strikes) < 4:
            return {}

        # Default initial guess for portfolio options
        if initial_guess is None:
            initial_guess = {
                "alpha": 0.2,
                "beta": 0.8,    # Slightly higher beta for equity portfolios
                "rho": -0.3,    # Negative correlation typical for equity options
                "nu": 0.4
            }

        # Simplified calibration using grid search
        best_params = initial_guess.copy()
        min_error = float('inf')
        
        # Grid search over parameter space
        for alpha in [0.1, 0.15, 0.2, 0.25, 0.3]:
            for beta in [0.5, 0.7, 0.9, 1.0]:
                for rho in [-0.7, -0.5, -0.3, 0.0, 0.3]:
                    for nu in [0.2, 0.3, 0.4, 0.5]:
                        error = self._calculate_calibration_error(
                            market_vols, strikes, F, T, alpha, beta, rho, nu
                        )
                        if error < min_error:
                            min_error = error
                            best_params = {
                                "alpha": alpha,
                                "beta": beta,
                                "rho": rho,
                                "nu": nu
                            }

        return best_params

    def _calculate_calibration_error(
        self,
        market_vols: list,
        strikes: list,
        F: float,
        T: float,
        alpha: float,
        beta: float,
        rho: float,
        nu: float,
    ) -> float:
        """Calculate sum of squared errors between market and model implied volatilities."""
        error = 0.0
        
        for market_vol, K in zip(market_vols, strikes):
            model_vol = self._sabr_implied_volatility(F, K, T, alpha, beta, rho, nu)
            if model_vol is not None:
                error += (market_vol - model_vol) ** 2
            else:
                error += 1e6  # Large penalty for invalid parameters

        return error

    def _norm_cdf(self, x: float) -> float:
        """Standard normal cumulative distribution function."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))