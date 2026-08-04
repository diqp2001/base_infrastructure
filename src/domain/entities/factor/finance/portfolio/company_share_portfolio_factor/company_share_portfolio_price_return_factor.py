from __future__ import annotations
from typing import Optional, Dict, Any, List
from decimal import Decimal

from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_factor import CompanySharePortfolioFactor


class CompanySharePortfolioPriceReturnFactor(CompanySharePortfolioFactor):
    """
    Return of a company-share portfolio measured between two portfolio price observations.

    Formula: (end_price - start_price) / start_price

    Branch A factor: the resolution service resolves the two lagged
    CompanySharePortfolioFactor (close price) dependencies whose lag offsets
    are stored in the FactorDependency table and passes them as
    {"start_price": Decimal, "end_price": Decimal} to calculate().
    """

    def __init__(
        self,
        name: str = "Company Share Portfolio Price Return",
        group: str = "return",
        subgroup: Optional[str] = "daily",
        frequency: Optional[str] = "1d",
        data_type: Optional[str] = "numeric",
        source: Optional[str] = "calculated",
        definition: Optional[str] = "Price return of a company share portfolio between two observations",
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
        return ["CompanySharePortfolioFactor"]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[Decimal]:
        try:
            start = dependencies.get("start_price")
            end = dependencies.get("end_price")
            if start is None or end is None:
                return None
            start = Decimal(str(start))
            end = Decimal(str(end))
            if start == 0:
                return None
            return (end - start) / start
        except Exception:
            return None
