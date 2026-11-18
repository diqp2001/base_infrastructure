"""
CompanyShareOptionValueFactor — the market value of a CompanyShareOption asset.

Value is determined by the CompanyShareOptionMidPriceFactor (the market's quotes); when the option has no quote
(e.g. an expired contract in a backtest: IBKR keeps no history of expired options), by its model price
(CompanyShareOptionModelPriceFactor: Black-Scholes on the underlying's close, IBKR implied vol and IRX). This factor bridges
a raw CompanyShareOption asset and holding-value calculations so portfolio logic
can use a generic 'asset value' concept rather than being tied to a specific
price factor name.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from decimal import Decimal

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_mid_price_factor import CompanyShareOptionMidPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_model_price_factor import CompanyShareOptionModelPriceFactor


class CompanyShareOptionValueFactor(CompanyShareOptionFactor):
    """
    Factor representing the market value of a CompanyShareOption.

    Dependencies:
        CompanyShareOptionMidPriceFactor — the mid price used to determine value.
    """

    def __init__(
        self,
        name: str = "company_share_option_value",
        group: str = "value",
        subgroup: Optional[str] = "asset",
        frequency: Optional[str] = "5m",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = "Market value of a company share option derived from mid price",
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            frequency=frequency,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
            **kwargs,
        )

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[Decimal]:
        """The option's mid price; without one, its model price."""
        raw = dependencies.get('CompanyShareOptionMidPriceFactor')
        if raw is None or raw == []:
            model = dependencies.get('CompanyShareOptionModelPriceFactor')
            values = [v for v in (model if isinstance(model, list) else [model]) if v is not None] if model else []
            return Decimal(str(values[-1])) if values and float(values[-1]) >= 0 else None
        if isinstance(raw, list):
            valid = [Decimal(str(v)) for v in raw if v is not None]
            if not valid:
                return None
            return sum(valid) / len(valid)
        if hasattr(raw, 'value'):
            return Decimal(str(raw.value))
        return Decimal(str(raw))



    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [
            
            DependencySpec(
                factor_type=CompanyShareOptionMidPriceFactor,
                group="price",
                frequency=DependencySpec.SELF,
                source_in=["calculated"],
            ),
            DependencySpec(
                factor_type=CompanyShareOptionModelPriceFactor,
                group="price_model",
                subgroup="black_scholes",
                source_in=["calculated"],
            ),

        ]