from typing import Optional

from domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor



class CompanyShareOptionDeltaFactor(CompanyShareOptionFactor):
    """Delta factor associated with a company share option."""

    def __init__(
        self,
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name="Option Delta",
            group="Option Greek",
            subgroup="Delta",
            data_type="float",
            source="model",
            definition="Rate of change of option value with respect to underlying price.",
            factor_id=factor_id,
            **kwargs,
        )
    def calculate_delta(
            self,
            S: float,        # underlying price
            K: float,        # strike
            r: float,        # interest rate
            sigma: float,    # volatility
            T: float,        # time to maturity in years
            option_type: str = "call",
        ) -> Optional[float]:

            

            d1, d2 = self._d1_d2(S, K, r, sigma, T)
            if d1 is None:
                return None

            if option_type.lower() == "call":
                return self._norm_cdf(d1)
            else:
                return self._norm_cdf(d1) - 1
