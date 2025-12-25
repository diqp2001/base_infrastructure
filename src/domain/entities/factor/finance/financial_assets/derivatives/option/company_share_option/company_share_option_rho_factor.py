import math
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor



class CompanyShareOptionRhoFactor(CompanyShareOptionFactor):
    """Rho factor associated with a company share option (sensitivity to interest rate)."""

    def __init__(
        self,
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name="Option Rho",
            group="Option Greek",
            subgroup="Rho",
            data_type="float",
            source="model",
            definition="Sensitivity of option value to interest rate changes.",
            factor_id=factor_id,
            **kwargs,
        )

    def calculate_rho(
        self,
        S: float,
        K: float,
        r: float,
        sigma: float,
        T: float,
        option_type: str = "call",
    ) -> Optional[float]:
        d1, d2 = self._d1_d2(S, K, r, sigma, T)
        if d1 is None or d2 is None:
            return None

        if option_type.lower() == "call":
            return K * T * math.exp(-r * T) * self._norm_cdf(d2)
        else:  # put
            return -K * T * math.exp(-r * T) * self._norm_cdf(-d2)
