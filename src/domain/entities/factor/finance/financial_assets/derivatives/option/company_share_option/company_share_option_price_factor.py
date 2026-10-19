import math
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionPriceFactor(CompanyShareOptionFactor):
    """BSM price factor for a company share option.

    Contract attributes (K, T, option_type) are read directly from the option entity
    and stored on this factor instance at creation time — they are not resolved as
    factor dependencies because they are static contract fields, not time-varying values.

    Dynamic dependencies (S, r, sigma) are resolved by the resolution service:
      - S     ← CompanyShareValueFactor   (underlying mid price × quantity)
      - r     ← CompanyShareOptionRFYieldFactor  (→ CurrencyYieldFactor chain)
      - sigma ← CompanyShareOptionImpliedVolFactor
    """

    def __init__(
        self,
        name: str = "option_price",
        group: str = "price_model",
        subgroup: Optional[str] = "black_scholes",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        frequency: Optional[str] = "1d",
        # Contract-level fields sourced from the option entity
        K: Optional[float] = None,
        T: float = 1.0,
        option_type: str = "call",
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
        self.K = K
        self.T = T
        self.option_type = option_type

    @property
    def calculate_dependencies(self) -> list:
        return ["CompanyShareValueFactor", "CompanyShareOptionRFYieldFactor", "CompanyShareOptionImpliedVolFactor"]

    def calculate(self, dependencies: dict) -> Optional[float]:
        """Compute BSM price from resolved factor dependencies + option contract attributes."""
        S = self._mean(dependencies.get("CompanyShareValueFactor"), positive=True)
        r = self._mean(dependencies.get("CompanyShareOptionRFYieldFactor"))
        sigma = self._mean(dependencies.get("CompanyShareOptionImpliedVolFactor"), positive=True)

        if S is None or r is None or sigma is None:
            return None

        # Contract terms come from the option the value is resolved for (strike, expiry measured at
        # the target date, call / put) — as the delta / gamma / vega / implied-vol factors do. The
        # factor's own K / T / option_type are only used when it is called without an option.
        entity = dependencies.get("entity")
        if entity is not None:
            terms = self._contract_terms(entity, dependencies.get("target_date"))
            if terms is None:
                return None
            K, T, option_type = terms
        else:
            K = self.K if self.K is not None else S  # ATM default
            T = self.T
            option_type = self.option_type

        d1, d2 = self._d1_d2(S, K, r, sigma, T)
        if d1 is None or d2 is None:
            return None

        if option_type.lower() == "call":
            return S * self._norm_cdf(d1) - K * math.exp(-r * T) * self._norm_cdf(d2)
        else:
            return K * math.exp(-r * T) * self._norm_cdf(-d2) - S * self._norm_cdf(-d1)

    @staticmethod
    def _mean(raw, positive: bool = False) -> Optional[float]:
        """Scalar or list dependency (DependencySpec delivers lists) -> mean of the usable values."""
        if raw is None:
            return None
        values = [float(v) for v in (raw if isinstance(raw, list) else [raw]) if v is not None]
        if positive:
            values = [v for v in values if v > 0]
        return sum(values) / len(values) if values else None

    @staticmethod
    def _contract_terms(entity, target_date):
        """(strike, years to expiry at target_date, 'call' | 'put') of the option, or None if unknown."""
        from datetime import date as _date, datetime as _dt
        strike = getattr(entity, "strike_price", None)
        expiry = getattr(entity, "end_date", None)
        if expiry is None and getattr(entity, "expiry", None):
            expiry = _dt.strptime(str(entity.expiry), "%Y%m%d").date()
        if strike is None or expiry is None:
            return None
        if hasattr(expiry, "date"):
            expiry = expiry.date()
        ref = target_date.date() if hasattr(target_date, "date") else (target_date or _date.today())
        days = (expiry - ref).days
        if days <= 0:
            return None
        return float(strike), days / 365.0, (getattr(entity, "option_type", None) or "call").lower()

    def _norm_cdf(self, x: float) -> float:
        """
        Standard normal cumulative distribution function.
        """
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def _d1_d2(
        self,
        S: float,
        K: float,
        r: float,
        sigma: float,
        T: float
    ) :
        """
        Compute Black-Scholes d1 and d2.
        """
        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return None, None

        try:
            d1 = (
                math.log(S / K)
                + (r + 0.5 * sigma ** 2) * T
            ) / (sigma * math.sqrt(T))

            d2 = d1 - sigma * math.sqrt(T)

            return d1, d2

        except (ValueError, ZeroDivisionError):
            return None, None

    # def calculate_price_sde(
    #     self,
    #     S: float,
    #     K: float,
    #     r: float,
    #     sigma: float,
    #     T: float,
    #     option_type: str = "call",
    #     n_paths: int = 10000,
    # ) -> Optional[float]:
    #     """
    #     Calculate option price using Monte Carlo simulation from Black-Scholes SDE:
    #     dS = r * S * dt + sigma * S * dW
    #     """
    #     if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
    #         return None

    #     payoffs: List[float] = []
    #     for _ in range(n_paths):
    #         # Simulate end-of-period price
    #         z = random.gauss(0, 1)
    #         ST = S * math.exp((r - 0.5 * sigma**2) * T + sigma * math.sqrt(T) * z)
    #         if option_type.lower() == "call":
    #             payoff = max(ST - K, 0)
    #         else:
    #             payoff = max(K - ST, 0)
    #         payoffs.append(payoff)

    #     discounted_payoff = math.exp(-r * T) * sum(payoffs) / n_paths
    #     return discounted_payoff

    # def calculate_price_pde(
    #     self,
    #     S: float,
    #     K: float,
    #     r: float,
    #     sigma: float,
    #     T: float,
    #     option_type: str = "call",
    #     S_max: Optional[float] = None,
    #     M: int = 100,      # price steps
    #     N: int = 100,      # time steps
    # ) -> Optional[float]:
    #     """
    #     Calculate option price using finite difference method (explicit) from Black-Scholes PDE:
    #     ∂V/∂t + 0.5*sigma^2*S^2*∂²V/∂S² + r*S*∂V/∂S - r*V = 0
    #     """
    #     if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
    #         return None

    #     S_max = S_max or 2 * K
    #     dt = T / N
    #     dS = S_max / M

    #     # Initialize asset prices and option values
    #     grid = [[0.0 for _ in range(M + 1)] for _ in range(N + 1)]
    #     S_values = [i * dS for i in range(M + 1)]

    #     # Terminal condition
    #     for i in range(M + 1):
    #         if option_type.lower() == "call":
    #             grid[N][i] = max(S_values[i] - K, 0)
    #         else:
    #             grid[N][i] = max(K - S_values[i], 0)

    #     # Backward induction
    #     for j in reversed(range(N)):
    #         for i in range(1, M):
    #             delta = (grid[j + 1][i + 1] - grid[j + 1][i - 1]) / (2 * dS)
    #             gamma = (grid[j + 1][i + 1] - 2 * grid[j + 1][i] + grid[j + 1][i - 1]) / (dS ** 2)
    #             grid[j][i] = grid[j + 1][i] + dt * (0.5 * sigma**2 * S_values[i]**2 * gamma + r * S_values[i] * delta - r * grid[j + 1][i])

    #         # Boundary conditions
    #         grid[j][0] = 0 if option_type.lower() == "call" else K * math.exp(-r * dt * (N - j))
    #         grid[j][M] = S_max - K * math.exp(-r * dt * (N - j)) if option_type.lower() == "call" else 0

    #     # Interpolate to find price at S
    #     i = int(S / dS)
    #     return grid[0][i]
