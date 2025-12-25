import math
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor



class CompanyShareOptionGammaFactor(CompanyShareOptionFactor):
    """Gamma factor associated with a company share option."""

    def __init__(
        self,
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name="Option Gamma",
            group="Option Greek",
            subgroup="Gamma",
            data_type="float",
            source="model",
            definition="Rate of change of Delta with respect to underlying price.",
            factor_id=factor_id,
            **kwargs,
        )
    def calculate_gamma(
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

            return self._norm_pdf(d1) / (S * sigma * math.sqrt(T))