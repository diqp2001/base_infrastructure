from __future__ import annotations
from typing import Optional, Dict, Any, List, Union
from decimal import Decimal

from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_factor import CompanySharePortfolioFactor


class CompanySharePortfolioEqualWeightReturnFactor(CompanySharePortfolioFactor):
    """
    Equal-weight average return of all CompanyShare components in a portfolio.

    Formula: mean(CompanySharePriceReturnFactor values for all holdings)

    Branch A factor: the resolution service fetches CompanySharePriceReturnFactor
    for each holding in the portfolio and passes them as
    {"CompanySharePriceReturnFactor": [Decimal, ...]} to calculate().
    """

    def __init__(
        self,
        name: str = "Company Share Portfolio Equal Weight Return",
        group: str = "return",
        subgroup: Optional[str] = "daily",
        frequency: Optional[str] = "1d",
        data_type: Optional[str] = "numeric",
        source: Optional[str] = "calculated",
        definition: Optional[str] = "Equal-weight average of all component CompanyShare returns",
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

    @property
    def calculate_dependencies(self) -> List[str]:
        return ["CompanySharePriceReturnFactor"]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[Decimal]:
        try:
            raw = dependencies.get("CompanySharePriceReturnFactor")
            if raw is None:
                return None
            if isinstance(raw, (int, float, Decimal)):
                return Decimal(str(raw))
            values = [Decimal(str(r)) for r in raw if r is not None]
            if not values:
                return None
            return sum(values) / Decimal(len(values))
        except Exception:
            return None
