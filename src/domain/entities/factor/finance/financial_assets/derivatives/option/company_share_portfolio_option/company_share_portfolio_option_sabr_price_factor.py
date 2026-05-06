import math
import random
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_factor import CompanySharePortfolioOptionFactor


class CompanySharePortfolioOptionSABRPriceFactor(CompanySharePortfolioOptionFactor):
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
        Calculate implied volatility using SABR formula approximation.
        """
        try:
            if abs(F - K) < 1e-10:  # ATM case
                # ATM approximation
                FK_mid = F
                factor1 = alpha / (FK_mid ** (1 - beta))
                
                factor2 = 1 + T * (
                    ((1 - beta)**2 * alpha**2) / (24 * FK_mid**(2 * (1 - beta))) +
                    (rho * beta * nu * alpha) / (4 * FK_mid**(1 - beta)) +
                    ((2 - 3 * rho**2) * nu**2) / 24
                )
                
                return factor1 * factor2
            
            else:  # Non-ATM case
                FK = F * K
                FK_mid = math.sqrt(FK)
                
                # Log-moneyness
                z = (nu / alpha) * (FK_mid**(1 - beta)) * math.log(F / K)
                
                # x(z) function
                if abs(z) < 1e-7:
                    x_z = 1
                else:
                    sqrt_term = math.sqrt(1 - 2*rho*z + z**2)
                    x_z = math.log((sqrt_term + z - rho) / (1 - rho)) / z
                
                # Main SABR formula
                numerator = alpha
                
                denominator = (FK_mid**(1 - beta)) * (
                    1 + ((1 - beta)**2 / 24) * (math.log(F / K))**2 +
                    ((1 - beta)**4 / 1920) * (math.log(F / K))**4
                )
                
                factor2 = 1 + T * (
                    ((1 - beta)**2 * alpha**2) / (24 * FK_mid**(2 * (1 - beta))) +
                    (rho * beta * nu * alpha) / (4 * FK_mid**(1 - beta)) +
                    ((2 - 3 * rho**2) * nu**2) / 24
                )
                
                return (numerator / denominator) * x_z * factor2

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def calibrate_sabr_parameters(
        self,
        market_data: dict,  # {(K, T): market_vol} market implied volatilities
        F: float,           # forward price
        initial_guess: dict = None,
    ) -> Optional[dict]:
        """
        Calibrate SABR parameters to market implied volatilities.
        
        This is a simplified implementation for demonstration.
        """
        if not market_data:
            return None
            
        if initial_guess is None:
            initial_guess = {
                "alpha": 0.2,
                "beta": 0.7,
                "rho": -0.3,
                "nu": 0.3
            }
        
        # In a real implementation, this would use optimization
        # For now, return the initial guess as a placeholder
        return initial_guess

    def calculate_sabr_greeks(
        self,
        F: float,
        K: float,
        T: float,
        alpha: float,
        beta: float,
        rho: float,
        nu: float,
        r: float = 0.0,
        option_type: str = "call",
        multiplier: int = 100,
    ) -> dict:
        """
        Calculate option Greeks using SABR model via finite differences.
        """
        try:
            # Base price
            base_price = self.calculate(F, K, T, alpha, beta, rho, nu, r, option_type, multiplier)
            if base_price is None:
                return {}

            # Delta (sensitivity to forward price)
            dF = F * 0.01
            price_up = self.calculate(F + dF, K, T, alpha, beta, rho, nu, r, option_type, multiplier)
            price_down = self.calculate(F - dF, K, T, alpha, beta, rho, nu, r, option_type, multiplier)
            
            delta = None
            if price_up is not None and price_down is not None:
                delta = (price_up - price_down) / (2 * dF)

            # Vega (sensitivity to alpha)
            dalpha = alpha * 0.01
            alpha_price = self.calculate(F, K, T, alpha + dalpha, beta, rho, nu, r, option_type, multiplier)
            
            vega = None
            if alpha_price is not None:
                vega = (alpha_price - base_price) / dalpha

            # Rho (sensitivity to correlation)
            drho = 0.01
            if abs(rho + drho) < 1:
                rho_price = self.calculate(F, K, T, alpha, beta, rho + drho, nu, r, option_type, multiplier)
                rho_sensitivity = (rho_price - base_price) / drho if rho_price is not None else None
            else:
                rho_sensitivity = None

            # Volga (sensitivity to nu)
            dnu = nu * 0.01
            nu_price = self.calculate(F, K, T, alpha, beta, rho, nu + dnu, r, option_type, multiplier)
            
            volga = None
            if nu_price is not None:
                volga = (nu_price - base_price) / dnu

            return {
                "price": base_price,
                "delta": delta,
                "vega": vega,
                "rho_sensitivity": rho_sensitivity,
                "volga": volga
            }

        except (ValueError, ZeroDivisionError, OverflowError):
            return {}

    def calculate_sabr_volatility_surface(
        self,
        F: float,
        strikes: list,
        expiries: list,
        alpha: float,
        beta: float,
        rho: float,
        nu: float,
    ) -> dict:
        """
        Generate SABR volatility surface for a range of strikes and expiries.
        """
        surface = {}
        
        for T in expiries:
            for K in strikes:
                if T > 0 and K > 0:
                    vol = self._sabr_implied_volatility(F, K, T, alpha, beta, rho, nu)
                    if vol is not None:
                        surface[(K, T)] = vol
        
        return surface

    def calculate_portfolio_sabr_option(
        self,
        forwards: list,        # [F1, F2, ..., Fn] individual forward prices
        weights: list,         # [w1, w2, ..., wn] portfolio weights
        K: float,              # strike price
        T: float,              # time to maturity
        alphas: list,          # [α1, α2, ..., αn] initial volatilities
        betas: list,           # [β1, β2, ..., βn] CEV exponents
        rho_matrix: list,      # correlation matrix
        nus: list,             # [ν1, ν2, ..., νn] volatilities of volatilities
        r: float = 0.0,        # risk-free rate
        option_type: str = "call",
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate portfolio option price where each asset follows SABR dynamics.
        
        This is a simplified approach using portfolio-level approximation.
        """
        if not forwards or not weights:
            return None
            
        n_assets = len(forwards)
        if (len(weights) != n_assets or len(alphas) != n_assets or 
            len(betas) != n_assets or len(nus) != n_assets):
            return None
            
        try:
            # Calculate portfolio forward
            portfolio_forward = sum(w * F for w, F in zip(weights, forwards))
            
            # Calculate portfolio SABR parameters (simplified approach)
            portfolio_alpha = sum(w * F / portfolio_forward * alpha 
                                for w, F, alpha in zip(weights, forwards, alphas))
            portfolio_beta = sum(w * F / portfolio_forward * beta 
                               for w, F, beta in zip(weights, forwards, betas))
            portfolio_nu = sum(w * F / portfolio_forward * nu 
                             for w, F, nu in zip(weights, forwards, nus))
            
            # Use average correlation for portfolio rho (simplified)
            if isinstance(rho_matrix[0], list):
                avg_rho = sum(sum(row) for row in rho_matrix) / (n_assets * n_assets)
            else:
                avg_rho = sum(rho_matrix) / len(rho_matrix)
            
            portfolio_rho = max(min(avg_rho, 0.99), -0.99)  # Keep within bounds
            
            # Calculate option price using portfolio SABR parameters
            return self.calculate(
                F=portfolio_forward,
                K=K,
                T=T,
                alpha=portfolio_alpha,
                beta=portfolio_beta,
                rho=portfolio_rho,
                nu=portfolio_nu,
                r=r,
                option_type=option_type,
                multiplier=multiplier
            )

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def _norm_cdf(self, x: float) -> float:
        """Standard normal cumulative distribution function."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))