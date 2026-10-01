from __future__ import annotations
from typing import List, Optional, Dict, Any
from decimal import Decimal

from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.dependency_spec import DependencySpec

from .company_share_portfolio_holding_factor import CompanySharePortfolioHoldingFactor
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare


class CompanySharePortfolioHoldingValueFactor(CompanySharePortfolioHoldingFactor):
    """
    Factor representing the total value of a company share holding in a portfolio.
    
    This factor is computed by multiplying the quantity factor (number of shares) 
    by the company share price factor to get the total monetary value of the holding.
    
    Value = Quantity × Price
    """

    def __init__(
        self,
        name: str = "Portfolio Company Share Holding Value",
        group: str = "holding",
        subgroup: Optional[str] = "value",
        frequency: Optional[str] = "5m",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = "Total value of company share holding (quantity × price)",
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
        price_vals = dependencies.get('CompanyShareValueFactor')
        quantity_raw = dependencies.get('Position')
        if not price_vals or quantity_raw is None:
            return None
        return Decimal(str(price_vals[0])) * Decimal(str(quantity_raw))

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import CompanyShareValueFactor
        return [
            DependencySpec(
                factor_type=CompanyShareValueFactor,
                group="value",
                subgroup="asset",
                source="calculated",
            ),
            'Position',
        ]