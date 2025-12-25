import math
from typing import Optional
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionVegaFactor(CompanyShareOptionFactor):
    """Vega factor associated with a company share option."""

    def __init__(
        self,
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name="Option Vega",
            group="Option Greek",
            subgroup="Vega",
            data_type="float",
            source="model",
            definition="Sensitivity of option value to implied volatility.",
            factor_id=factor_id,
            **kwargs,
        )
    def calculate_vega(
            self,
            S: float,
            K: float,
            r: float,
            sigma: float,
            T: float,
        ) -> Optional[float]:


            d1, d2 = self._d1_d2(S, K, r, sigma, T)
            if d1 is None:
                return None

            # Note: Vega is per % volatility change → multiply by 0.01 if needed
            return S * self._norm_pdf(d1) * math.sqrt(T)