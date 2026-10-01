"""
CompanyShareOptionValueFactor — the market value of a CompanyShareOption asset.

Value is determined by the CompanyShareOptionMidPriceFactor. This factor bridges
a raw CompanyShareOption asset and holding-value calculations so portfolio logic
can use a generic 'asset value' concept rather than being tied to a specific
price factor name.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from decimal import Decimal

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_mid_price_factor import CompanyShareOptionMidPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


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
        """Return the option mid price as the value of the company share option."""
        raw = dependencies.get('CompanyShareOptionMidPriceFactor')
        if raw is None:
            return None
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
            
        ]