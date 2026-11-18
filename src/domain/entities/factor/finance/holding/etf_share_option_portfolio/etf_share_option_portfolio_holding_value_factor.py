from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from src.domain.entities.factor.dependency_spec import DependencySpec
from src.domain.entities.factor.finance.holding.portfolio_holding_factor import PortfolioHoldingFactor


class ETFShareOptionPortfolioHoldingValueFactor(PortfolioHoldingFactor):
    """
    Value of an ETF share option holding in an ETFShareOptionPortfolio:
        option value (ETFShareOptionValueFactor) x contracts (Position) x contract multiplier (Asset.multiplier).
    """

    def __init__(self, name: str = "Portfolio ETF Share Option Holding Value", group: str = "holding",
                 subgroup: Optional[str] = "value", frequency: Optional[str] = "1d",
                 data_type: Optional[str] = "decimal", source: Optional[str] = "calculated",
                 definition: Optional[str] = "Total value of ETF share option holding (quantity x price x multiplier)",
                 factor_id: Optional[int] = None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency, data_type=data_type,
                         source=source, definition=definition, factor_id=factor_id)

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[Decimal]:
        price_vals = dependencies.get('ETFShareOptionValueFactor')
        quantity_raw = dependencies.get('Position')
        multiplier = dependencies.get('Asset.multiplier')
        if not price_vals or quantity_raw is None or multiplier is None:
            return None
        return Decimal(str(price_vals[0])) * Decimal(str(quantity_raw)) * Decimal(str(multiplier))

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_value_factor import (
            ETFShareOptionValueFactor,
        )
        return [
            DependencySpec(factor_type=ETFShareOptionValueFactor, group="value", subgroup="asset",
                           source="calculated"),
            'Position',
            'Asset.multiplier',
        ]
