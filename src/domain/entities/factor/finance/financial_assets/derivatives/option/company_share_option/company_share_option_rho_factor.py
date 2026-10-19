import math
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.option_market_inputs import OptionMarketInputs
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor



class CompanyShareOptionRhoFactor(OptionMarketInputs, CompanyShareOptionFactor):
    """Rho factor associated with a company share option (sensitivity to interest rate)."""

    def __init__(
        self,
        name: str = "rho",
        group: str = "greek",
        subgroup: Optional[str] = "rho",
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
        from the option at the target date. Direct callers: the explicit arguments of rho()."""
        if isinstance(dependencies, dict):
            inputs = self.market_inputs(dependencies)
            return None if inputs is None else self.rho(**inputs)
        if dependencies is not None:
            args = (dependencies,) + args
        return self.rho(*args, **kwargs)

    def rho(
        self,
        S: float,
        K: float,
        r: float,
        sigma: float,
        T: float,
        option_type: str = "call",
    ) -> Optional[float]:
        side = self._option_side(option_type)
        d1, d2 = self._d1_d2(S, K, r, sigma, T)
        if side is None or d1 is None or d2 is None:
            return None

        if side == "call":
            return K * T * math.exp(-r * T) * self._norm_cdf(d2)
        else:  # put
            return -K * T * math.exp(-r * T) * self._norm_cdf(-d2)

    @staticmethod
    def _d1_d2(S, K, r, sigma, T):
        """Black-Scholes d1, d2 (no dividend); (None, None) for invalid inputs."""
        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return None, None
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        return d1, d1 - sigma * math.sqrt(T)

    @staticmethod
    def _norm_cdf(x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

