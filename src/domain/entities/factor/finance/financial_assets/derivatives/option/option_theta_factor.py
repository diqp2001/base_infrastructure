import math
from typing import Optional
from domain.entities.factor.finance.financial_assets.derivatives.option.option_factor import OptionFactor


class OptionThetaFactor(OptionFactor):
    """Theta factor associated with a company share option."""

    def __init__(
        self,
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name="Option Theta",
            group="Option Greek",
            subgroup="Theta",
            data_type="float",
            source="model",
            definition="Sensitivity of option value to time value",
            factor_id=factor_id,
            **kwargs,
        )
    