from __future__ import annotations
from typing import Optional

from ..portfolio_factor import PortfolioFactor


class PortfolioCompanyShareFactor(PortfolioFactor):
    """
    Domain entity representing a portfolio factor specific to
    portfolios composed of company shares (equities).

    Identification-only factor.
    """

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
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
