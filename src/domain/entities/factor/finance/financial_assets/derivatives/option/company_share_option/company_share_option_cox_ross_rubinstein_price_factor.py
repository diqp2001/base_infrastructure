import math
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.option_market_inputs import OptionMarketInputs
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionCoxRossRubinsteinPriceFactor(OptionMarketInputs, CompanyShareOptionFactor):
    """Cox-Ross-Rubinstein binomial tree price factor for company share options."""

    def __init__(
        self,
        name: str = "cox_ross_rubinstein_price",
        group: str = "price_model",
        subgroup: Optional[str] = "binomial_tree",
        data_type: Optional[str] = "numeric",
        source: Optional[str] = "calculated",
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        frequency: Optional[str] = "1d",
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
            frequency=frequency,
            **kwargs,
        )

    def calculate(self, dependencies=None, *args, **kwargs) -> Optional[float]:
        """Resolution service: calculate(dependencies) with S / sigma / r resolved and K / T / call-put taken
        from the option at the target date. Direct callers: the explicit arguments of price()."""
        if isinstance(dependencies, dict):
            inputs = self.market_inputs(dependencies)
            return None if inputs is None else self.price(**inputs)
        if dependencies is not None:
            args = (dependencies,) + args
        return self.price(*args, **kwargs)

    def price(
        self,
        S: float,          # underlying price
        K: float,          # strike price
        r: float,          # risk-free rate
        sigma: float,      # volatility
        T: float,          # time to maturity in years
        q: float = 0.0,    # dividend yield
        option_type: str = "call",
        steps: int = 100,  # number of time steps
        american: bool = False,  # American vs European option
    ) -> Optional[float]:
        """
        Calculate option price using Cox-Ross-Rubinstein binomial tree model.
        
        The CRR model uses a recombining binomial tree with:
        - Up factor: u = e^(σ*√(Δt))
        - Down factor: d = 1/u
        - Risk-neutral probability: p = (e^((r-q)*Δt) - d) / (u - d)
        """
        side = self._option_side(option_type)
        if side is None or S <= 0 or K <= 0 or sigma <= 0 or T <= 0 or steps <= 0:
            return None

        try:
            dt = T / steps
            u = math.exp(sigma * math.sqrt(dt))  # up factor
            d = 1 / u                            # down factor
            p = (math.exp((r - q) * dt) - d) / (u - d)  # risk-neutral probability

            # Validate probability
            if p < 0 or p > 1:
                return None

            # Initialize asset prices at maturity
            asset_prices = []
            for i in range(steps + 1):
                asset_prices.append(S * (u ** (steps - i)) * (d ** i))

            # Initialize option values at maturity
            option_values = []
            for i in range(steps + 1):
                if side == "call":
                    option_values.append(max(asset_prices[i] - K, 0))
                else:  # put
                    option_values.append(max(K - asset_prices[i], 0))

            # Work backwards through the tree
            for step in range(steps - 1, -1, -1):
                new_option_values = []
                for i in range(step + 1):
                    # Current asset price at this node
                    current_asset_price = S * (u ** (step - i)) * (d ** i)
                    
                    # Calculate option value by discounting expected payoff
                    discounted_value = math.exp(-r * dt) * (p * option_values[i] + (1 - p) * option_values[i + 1])
                    
                    # For American options, check early exercise
                    if american:
                        if side == "call":
                            exercise_value = max(current_asset_price - K, 0)
                        else:  # put
                            exercise_value = max(K - current_asset_price, 0)
                        
                        option_value = max(discounted_value, exercise_value)
                    else:
                        option_value = discounted_value
                    
                    new_option_values.append(option_value)
                
                option_values = new_option_values

            return option_values[0]

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
        steps: int = 100,
        american: bool = False,
    ) -> dict:
        """Calculate option Greeks using finite differences in the binomial tree."""
        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return {}

        try:
            # Calculate base price
            base_price = self.price(S, K, r, sigma, T, q, option_type, steps, american)
            if base_price is None:
                return {}

            # Delta: sensitivity to underlying price
            dS = S * 0.01  # 1% shift
            price_up = self.price(S + dS, K, r, sigma, T, q, option_type, steps, american)
            price_down = self.price(S - dS, K, r, sigma, T, q, option_type, steps, american)
            
            if price_up is not None and price_down is not None:
                delta = (price_up - price_down) / (2 * dS)
                # Gamma: second derivative with respect to S
                gamma = (price_up - 2 * base_price + price_down) / (dS ** 2)
            else:
                delta = gamma = None

            # Theta: sensitivity to time
            dT = T * 0.01  # 1% shift in time
            if T - dT > 0:
                price_theta = self.price(S, K, r, sigma, T - dT, q, option_type, steps, american)
                theta = (price_theta - base_price) / dT if price_theta is not None else None
            else:
                theta = None

            # Vega: sensitivity to volatility
            dsigma = sigma * 0.01  # 1% shift
            price_vega = self.price(S, K, r, sigma + dsigma, T, q, option_type, steps, american)
            vega = (price_vega - base_price) / dsigma if price_vega is not None else None

            # Rho: sensitivity to interest rate
            dr = r * 0.01  # 1% shift
            price_rho = self.price(S, K, r + dr, sigma, T, q, option_type, steps, american)
            rho = (price_rho - base_price) / dr if price_rho is not None else None

            return {
                "delta": delta,
                "gamma": gamma,
                "theta": theta,
                "vega": vega,
                "rho": rho
            }

        except (ValueError, ZeroDivisionError, OverflowError):
            return {}