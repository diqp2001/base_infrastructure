from __future__ import annotations
from typing import Optional

from .portfolio_holding_factor import PortfolioHoldingFactor


class PortfolioCompanyShareHoldingFactor(PortfolioHoldingFactor):
    """
    Factor for holdings of company shares inside a PortfolioCompanyShare.

    Identification-only. Metrics like weight, price, contribution, etc.,
    are handled as FactorValues.
    """

    def __init__(
        self,
        name: str,
        group: str = "holding",
        subgroup: Optional[str] = "company_share",
        data_type: Optional[str] = "identifier",
        source: Optional[str] = "portfolio_management",
        definition: Optional[str] = "Company share holding within portfolio",
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
