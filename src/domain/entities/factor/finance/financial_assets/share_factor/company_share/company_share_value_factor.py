"""
CompanyShareValueFactor — the market value of a CompanyShare asset.

Value is determined by the CompanyShareMidPriceFactor. This factor acts as
the bridge between a raw CompanyShare asset and the holding-value calculation
so that any portfolio logic can use a generic 'asset value' concept rather
than being tied to a specific price factor name.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from decimal import Decimal

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor


class CompanyShareValueFactor(CompanyShareFactor):
    """
    Factor representing the market value of a CompanyShare.

    Dependencies:
        company_share_mid_price_factor — the mid price used to determine value.
    """

    def __init__(
        self,
        name: str = "company_share_value",
        group: str = "value",
        subgroup: Optional[str] = "asset",
        frequency: Optional[str] = "1d",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = "Market value of a company share derived from mid price",
        factor_id: Optional[int] = None,
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
        )

    def calculate(self, dependencies: Dict[str, Any]) -> Decimal:
        """
        Return the mid price as the value of the company share.

        Args:
            dependencies: dict containing:
                'company_share_mid_price_factor': Decimal or object with .value
        """
        raw = dependencies.get('company_share_mid_price_factor', Decimal('0'))
        if hasattr(raw, 'value'):
            return Decimal(str(raw.value))
        return Decimal(str(raw))

    def get_dependencies(self) -> List[str]:
        return ['company_share_mid_price_factor']
