"""
CurrencyValueFactor — the market value of a Currency asset.

Value is determined by the CurrencyMidPriceFactor (exchange rate). This factor
acts as the bridge between a raw Currency asset and the holding-value calculation
so that portfolio logic can use a generic 'asset value' concept.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from decimal import Decimal

from src.domain.entities.factor.finance.financial_assets.currency.currency_factor import CurrencyFactor


class CurrencyValueFactor(CurrencyFactor):
    """
    Factor representing the market value of a Currency asset.

    Dependencies:
        currency_mid_price_factor — the exchange rate used to determine value.
    """

    def __init__(
        self,
        name: str = "currency_value",
        group: str = "value",
        subgroup: Optional[str] = "asset",
        frequency: Optional[str] = "1d",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = "Market value of a currency asset derived from mid price",
        factor_id: Optional[int] = None,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
        )
        self.frequency = frequency

    def calculate(self, dependencies: Dict[str, Any]) -> Decimal:
        """
        Return the mid price as the value of the currency.

        Args:
            dependencies: dict containing:
                'currency_mid_price_factor': Decimal or object with .value
        """
        raw = dependencies.get('currency_mid_price_factor', Decimal('1'))
        if hasattr(raw, 'value'):
            return Decimal(str(raw.value))
        return Decimal(str(raw))

    @property
    def calculate_dependencies(self) -> List[str]:
        return ['CurrencyRateFactor']
