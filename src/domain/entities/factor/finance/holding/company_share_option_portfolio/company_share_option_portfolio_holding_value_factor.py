from __future__ import annotations
from typing import List, Optional, Dict, Any
from decimal import Decimal

from src.domain.entities.factor.finance.holding.portfolio_holding_factor import PortfolioHoldingFactor
from src.domain.entities.factor.dependency_spec import DependencySpec


class CompanyShareOptionPortfolioHoldingValueFactor(PortfolioHoldingFactor):
    """
    Factor representing the total value of a company share option holding in a portfolio.

    Value = Quantity × CompanyShareOptionValueFactor
    """

    def __init__(
        self,
        name: str = "Portfolio Company Share Option Holding Value",
        group: str = "holding",
        subgroup: Optional[str] = "value",
        frequency: Optional[str] = "5m",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = "Total value of company share option holding (quantity × price)",
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

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[Decimal]:
        """Option premium × contracts × contract multiplier (a contract on 100 shares is worth 100 × the quoted
        premium); no multiplier, no value."""
        price_vals = dependencies.get('CompanyShareOptionValueFactor')
        quantity_raw = dependencies.get('Position')
        multiplier = dependencies.get('Asset.multiplier')
        if not price_vals or quantity_raw is None or multiplier is None:
            return None
        return Decimal(str(price_vals[0])) * Decimal(str(quantity_raw)) * Decimal(str(multiplier))

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_value_factor import CompanyShareOptionValueFactor
        return [
            DependencySpec(
                factor_type=CompanyShareOptionValueFactor,
                group="value",
                subgroup="asset",
                source="calculated",
            ),
            'Position',
            'Asset.multiplier',
        ]
