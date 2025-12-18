
from __future__ import annotations
from typing import Optional

from .holding_factor import HoldingFactor


class PortfolioHoldingFactor(HoldingFactor):
    """
    Factor for holdings inside a portfolio.

    Identification-only. Values like weights, returns, exposure live elsewhere.
    """

    def __init__(
        self,
        name: str,
        group: str = "holding",
        subgroup: Optional[str] = "portfolio",
        data_type: Optional[str] = "identifier",
        source: Optional[str] = "portfolio_management",
        definition: Optional[str] = "Holding within a portfolio",
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
