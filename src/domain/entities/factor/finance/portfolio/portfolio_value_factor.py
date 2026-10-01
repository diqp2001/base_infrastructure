

"""
src/domain/entities/factor/finance/portfolio/portfolio_value_factor.py

PortfolioValueFactor domain entity - calculates portfolio value from holding values.
"""

from typing import Optional, Dict, Any, List
from decimal import Decimal

from src.domain.entities.factor.finance.portfolio.portfolio_factor import PortfolioFactor
from src.domain.entities.factor.dependency_spec import DependencySpec


class PortfolioValueFactor(PortfolioFactor):
    """Domain entity representing a portfolio value factor that calculates total portfolio value."""

    def __init__(
        self,
        name: str = "Portfolio Value",
        group: str = "value",
        subgroup: Optional[str] = "daily",
        frequency: Optional[str] = '5m',
        data_type: Optional[str] = 'numeric',
        source: Optional[str] = 'calculated',
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
    ):
        if definition is None:
            definition = f"Portfolio value factor: {name}"
            
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
        try:
            total_value = Decimal('0.0')
            for key, vals in dependencies.items():
                if key in ('entity', 'target_date'):
                    continue
                if isinstance(vals, list):
                    for v in vals:
                        if isinstance(v, (int, float, Decimal)):
                            total_value += Decimal(str(v))
            return total_value
        except Exception as e:
            print(f"Error calculating portfolio value: {e}")
            return Decimal('0.0')
    
    @property
    def calculate_dependencies(self) -> List[DependencySpec]:
        from src.domain.entities.factor.finance.holding.currency_portfolio_portfolio.currency_portfolio_portfolio_holding_value_factor import CurrencyPortfolioPortfolioHoldingValueFactor
        from src.domain.entities.factor.finance.holding.company_share_portfolio_portfolio.company_share_portfolio_portfolio_holding_value_factor import CompanySharePortfolioPortfolioHoldingValueFactor
        from src.domain.entities.factor.finance.holding.company_share_option_portfolio_portfolio.company_share_option_portfolio_portfolio_holding_value_factor import CompanyShareOptionPortfolioPortfolioHoldingValueFactor
        return [
            DependencySpec(
                factor_type=CurrencyPortfolioPortfolioHoldingValueFactor,
                group="holding",
                subgroup="value",
                source="calculated",
            ),
            DependencySpec(
                factor_type=CompanySharePortfolioPortfolioHoldingValueFactor,
                group="holding",
                subgroup="value",
                source="calculated",
            ),
            DependencySpec(
                factor_type=CompanyShareOptionPortfolioPortfolioHoldingValueFactor,
                group="holding",
                subgroup="value",
                source="calculated",
            ),
        ]
