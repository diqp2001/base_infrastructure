from __future__ import annotations
from typing import Optional

from .portfolio_company_share_holding_factor import PortfolioCompanyShareHoldingFactor


class PortfolioCompanyShareHoldingWeightFactor(PortfolioCompanyShareHoldingFactor):
    """
    Factor representing the weight of a company share within a PortfolioCompanyShare.

    Identification-only. The actual weight values are stored as FactorValues
    keyed by portfolio, holding, and date.
    """

    def __init__(
        self,
        name: str = "Portfolio Company Share Holding Weight",
        group: str = "holding",
        subgroup: Optional[str] = "weight",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "portfolio_management",
        definition: Optional[str] = "Weight of company share holding within portfolio",
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
