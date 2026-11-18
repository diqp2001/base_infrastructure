"""
CompanyShareOptionModelPriceFactor - the model price of an option on a company share when the market has no quote
for it: Black-Scholes-Merton on the underlying's close, its IBKR implied volatility and the IRX rate
(share_option_model_price). The fallback of CompanyShareOptionValueFactor.
"""

from __future__ import annotations

from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import (
    CompanyShareOptionFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.share_option_model_price import (
    model_price,
    model_price_dependency_specs,
)


class CompanyShareOptionModelPriceFactor(CompanyShareOptionFactor):

    def __init__(self, name: str = "company_share_option_model_price", group: str = "price_model",
                 subgroup: Optional[str] = "black_scholes", frequency: Optional[str] = "1d",
                 data_type: Optional[str] = "decimal", source: Optional[str] = "calculated",
                 definition: Optional[str] = "Black-Scholes-Merton price on the underlying's close, IBKR implied "
                                             "volatility and the IRX rate (no market quote)",
                 factor_id: Optional[int] = None, **kwargs):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency, data_type=data_type,
                         source=source, definition=definition, factor_id=factor_id, **kwargs)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
            CompanyShareFactor,
        )
        return model_price_dependency_specs(CompanyShareFactor)

    def calculate(self, dependencies: dict) -> Optional[float]:
        return model_price(dependencies)
