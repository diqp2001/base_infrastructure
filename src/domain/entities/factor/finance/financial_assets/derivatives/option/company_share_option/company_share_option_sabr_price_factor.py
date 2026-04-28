import math
import random
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionSABRPriceFactor(CompanyShareOptionFactor):
    """SABR (Stochastic Alpha Beta Rho) price factor for company share options."""

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
        F: float,          # forward price
        K: float,          # strike price
        T: float,          # time to maturity in years
        alpha: float,      # initial volatility
        beta: float,       # CEV exponent (0 <= beta <= 1)
        rho: float,        # correlation between forward and volatility
        nu: float,         # volatility of volatility
        r: float = 0.0,    # risk-free rate for discounting
        option_type: str = "call",
    ) -> Optional[float]:
        """
        Calculate option price using SABR model via implied volatility approach.
        
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

            return price

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

    def calculate_monte_carlo(
        self,
        F0: float,         # initial forward price
        K: float,          # strike price
        T: float,          # time to maturity
        alpha0: float,     # initial volatility
        beta: float,       # CEV exponent
        rho: float,        # correlation
        nu: float,         # volatility of volatility
        r: float = 0.0,    # risk-free rate
        option_type: str = "call",
        n_paths: int = 50000,
        n_steps: int = 252,
    ) -> Optional[float]:
        """
        Calculate option price using Monte Carlo simulation of SABR dynamics.
        """
        if F0 <= 0 or K <= 0 or T <= 0 or alpha0 <= 0 or beta < 0 or beta > 1:
            return None
        if abs(rho) >= 1 or nu < 0:
            return None

        try:
            dt = T / n_steps
            sqrt_dt = math.sqrt(dt)
            
            payoffs = []
            
            for _ in range(n_paths):
                F_t = F0
                alpha_t = alpha0
                
                for _ in range(n_steps):
                    # Generate correlated random numbers
                    z1 = random.gauss(0, 1)
                    z2 = rho * z1 + math.sqrt(1 - rho * rho) * random.gauss(0, 1)
                    
                    # Ensure positive values
                    F_t = max(F_t, 1e-8)
                    alpha_t = max(alpha_t, 1e-8)
                    
                    # Update forward price using CEV process
                    dF = alpha_t * (F_t ** beta) * sqrt_dt * z1
                    F_t += dF
                    F_t = max(F_t, 0)  # Ensure non-negative
                    
                    # Update volatility
                    dalpha = nu * alpha_t * sqrt_dt * z2
                    alpha_t += dalpha
                    alpha_t = max(alpha_t, 1e-8)  # Ensure positive volatility
                
                # Calculate payoff
                if option_type.lower() == "call":
                    payoff = max(F_t - K, 0)
                else:  # put
                    payoff = max(K - F_t, 0)
                
                payoffs.append(payoff)
            
            # Discount the expected payoff
            option_price = math.exp(-r * T) * sum(payoffs) / len(payoffs)
            return option_price

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def calibrate_sabr_parameters(
        self,
        market_vols: list,      # market implied volatilities
        strikes: list,          # strike prices
        F: float,               # forward price
        T: float,               # time to maturity
        initial_guess: dict = None,  # initial parameter guess
    ) -> dict:
        """
        Calibrate SABR parameters to market implied volatilities.
        
        This is a simplified implementation. In practice, sophisticated
        optimization algorithms would be used.
        """
        if len(market_vols) != len(strikes) or len(strikes) < 4:
            return {}

        # Default initial guess
        if initial_guess is None:
            initial_guess = {
                "alpha": 0.2,
                "beta": 0.5,
                "rho": 0.0,
                "nu": 0.3
            }

        # This is a placeholder for parameter calibration
        # In practice, would use optimization methods like Levenberg-Marquardt
        best_params = initial_guess.copy()
        
        # Simple grid search (very basic implementation)
        min_error = float('inf')
        
        for alpha in [0.1, 0.2, 0.3]:
            for beta in [0.0, 0.5, 1.0]:
                for rho in [-0.5, 0.0, 0.5]:
                    for nu in [0.1, 0.3, 0.5]:
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