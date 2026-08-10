from decimal import Decimal
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_factor import CompanySharePortfolioOptionFactor


class CompanySharePortfolioOptionValueFactor(CompanySharePortfolioOptionFactor):
    """Market value of a company share portfolio option position (price × multiplier × contracts)."""

    def __init__(
        self,
        name: str = "value",
        group: str = "value",
        subgroup: Optional[str] = "asset",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        frequency: Optional[str] = "1d",
        **kwargs,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
            frequency=frequency,
            **kwargs,
        )

    def calculate(
        self,
        price: float,
        multiplier: int = 100,
        contracts: int = 1,
    ) -> Optional[Decimal]:
        if price is None or price <= 0:
            return Decimal("0")
        return Decimal(str(price)) * Decimal(str(multiplier)) * Decimal(str(contracts))
