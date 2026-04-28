import math
from typing import Optional
import numpy as np

from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_factor import PortfolioCompanyShareOptionFactor


class PortfolioCompanyShareOptionBlackScholesMertonPriceFactor(PortfolioCompanyShareOptionFactor):
    """Black-Scholes-Merton price factor for portfolio company share options with dividend yield."""

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
        sigma: float,      # portfolio volatility
        T: float,          # time to maturity in years
        q: float = 0.0,    # portfolio dividend yield
        option_type: str = "call",
        multiplier: int = 100,  # contract multiplier
    ) -> Optional[float]:
        """
        Calculate portfolio option price using Black-Scholes-Merton formula with dividend yield.
        
        For portfolio options, the underlying is typically a portfolio of stocks or an index,
        which may pay dividends continuously at rate q.
        
        The BSM formula:
        - Call: S*e^(-q*T)*N(d1) - K*e^(-r*T)*N(d2)
        - Put: K*e^(-r*T)*N(-d2) - S*e^(-q*T)*N(-d1)
        
        Where:
        d1 = [ln(S/K) + (r - q + σ²/2)*T] / (σ*√T)
        d2 = d1 - σ*√T
        """
        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return None

        try:
            # Calculate d1 and d2 with dividend yield adjustment
            d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)

            # Calculate option price with dividend adjustment
            if option_type.lower() == "call":
                price = (S * math.exp(-q * T) * self._norm_cdf(d1) - 
                        K * math.exp(-r * T) * self._norm_cdf(d2))
            else:  # put
                price = (K * math.exp(-r * T) * self._norm_cdf(-d2) - 
                        S * math.exp(-q * T) * self._norm_cdf(-d1))

            return price * multiplier

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def calculate_basket_option(
        self,
        spot_prices: list,     # [S1, S2, ..., Sn] individual asset prices
        weights: list,         # [w1, w2, ..., wn] portfolio weights
        K: float,              # strike price
        r: float,              # risk-free rate
        T: float,              # time to maturity
        correlations: list,    # correlation matrix (flat list or 2D)
        volatilities: list,    # [σ1, σ2, ..., σn] individual volatilities
        dividend_yields: list = None,  # [q1, q2, ..., qn] individual dividend yields
        option_type: str = "call",
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate basket/portfolio option price using portfolio approach.
        
        The portfolio volatility is calculated as:
        σ_p² = Σᵢ Σⱼ wᵢ wⱼ σᵢ σⱼ ρᵢⱼ
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

            # Calculate portfolio value
            portfolio_value = sum(w * S for w, S in zip(weights, spot_prices))
            
            # Calculate portfolio dividend yield
            portfolio_dividend_yield = sum(w * S * q for w, S, q in zip(weights, spot_prices, dividend_yields)) / portfolio_value

            # Calculate portfolio volatility
            portfolio_variance = 0.0
            
            # Handle correlation matrix
            if isinstance(correlations[0], list):
                # 2D correlation matrix
                corr_matrix = correlations
            else:
                # Flat correlation matrix - convert to 2D
                corr_matrix = []
                idx = 0
                for i in range(n_assets):
                    row = []
                    for j in range(n_assets):
                        if i == j:
                            row.append(1.0)
                        elif j > i:
                            row.append(correlations[idx])
                            idx += 1
                        else:
                            row.append(corr_matrix[j][i])
                    corr_matrix.append(row)

            # Calculate portfolio variance
            for i in range(n_assets):
                for j in range(n_assets):
                    weight_i = weights[i] * spot_prices[i] / portfolio_value
                    weight_j = weights[j] * spot_prices[j] / portfolio_value
                    portfolio_variance += weight_i * weight_j * volatilities[i] * volatilities[j] * corr_matrix[i][j]

            portfolio_volatility = math.sqrt(max(portfolio_variance, 1e-10))

            # Calculate option price using portfolio parameters
            return self.calculate(
                S=portfolio_value,
                K=K,
                r=r,
                sigma=portfolio_volatility,
                T=T,
                q=portfolio_dividend_yield,
                option_type=option_type,
                multiplier=multiplier
            )

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def calculate_greeks(
        self,
        S: float,
        K: float,
        r: float,
        sigma: float,
        T: float,
        q: float = 0.0,
        option_type: str = "call",
        multiplier: int = 100,
    ) -> dict:
        """Calculate option Greeks for portfolio options."""
        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return {}

        try:
            d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            
            nd1 = self._norm_cdf(d1)
            nd2 = self._norm_cdf(d2)
            n_prime_d1 = self._norm_pdf(d1)
            
            if option_type.lower() == "call":
                delta = math.exp(-q * T) * nd1 * multiplier
                theta = (-(S * n_prime_d1 * sigma * math.exp(-q * T)) / (2 * math.sqrt(T)) - 
                        r * K * math.exp(-r * T) * nd2 + q * S * math.exp(-q * T) * nd1) * multiplier
                rho = K * T * math.exp(-r * T) * nd2 * multiplier
            else:  # put
                delta = math.exp(-q * T) * (nd1 - 1) * multiplier
                theta = (-(S * n_prime_d1 * sigma * math.exp(-q * T)) / (2 * math.sqrt(T)) + 
                        r * K * math.exp(-r * T) * self._norm_cdf(-d2) - q * S * math.exp(-q * T) * self._norm_cdf(-d1)) * multiplier
                rho = -K * T * math.exp(-r * T) * self._norm_cdf(-d2) * multiplier
            
            gamma = (n_prime_d1 * math.exp(-q * T)) / (S * sigma * math.sqrt(T)) * multiplier
            vega = S * math.exp(-q * T) * n_prime_d1 * math.sqrt(T) * multiplier
            
            return {
                "delta": delta,
                "gamma": gamma,
                "theta": theta,
                "vega": vega,
                "rho": rho
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
        volatilities: list,
        dividend_yields: list = None,
        option_type: str = "call",
        multiplier: int = 100,
    ) -> dict:
        """Calculate Greeks for the entire portfolio option with respect to individual assets."""
        if not spot_prices or not weights or not volatilities:
            return {}

        try:
            # Calculate base price
            base_price = self.calculate_basket_option(
                spot_prices, weights, K, r, T, correlations, volatilities,
                dividend_yields, option_type, multiplier
            )
            
            if base_price is None:
                return {}

            # Calculate individual deltas (sensitivity to each underlying)
            individual_deltas = []
            dS = 0.01  # 1% shift
            
            for i in range(len(spot_prices)):
                spot_prices_up = spot_prices.copy()
                spot_prices_down = spot_prices.copy()
                
                spot_prices_up[i] *= (1 + dS)
                spot_prices_down[i] *= (1 - dS)
                
                price_up = self.calculate_basket_option(
                    spot_prices_up, weights, K, r, T, correlations, volatilities,
                    dividend_yields, option_type, multiplier
                )
                price_down = self.calculate_basket_option(
                    spot_prices_down, weights, K, r, T, correlations, volatilities,
                    dividend_yields, option_type, multiplier
                )
                
                if price_up is not None and price_down is not None:
                    delta_i = (price_up - price_down) / (2 * spot_prices[i] * dS)
                    individual_deltas.append(delta_i)
                else:
                    individual_deltas.append(0.0)

            # Calculate cross-gammas (sensitivity to correlation changes)
            cross_gammas = []
            drho = 0.01
            
            # This is simplified - full implementation would calculate all cross-gammas
            
            return {
                "individual_deltas": individual_deltas,
                "cross_gammas": cross_gammas,
                "total_delta": sum(individual_deltas),
                "base_price": base_price
            }

        except (ValueError, ZeroDivisionError, OverflowError):
            return {}

    def _norm_cdf(self, x: float) -> float:
        """Standard normal cumulative distribution function."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def _norm_pdf(self, x: float) -> float:
        """Standard normal probability density function."""
        return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)