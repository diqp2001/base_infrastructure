from __future__ import annotations
from typing import Optional

from domain.entities.factor.finance.financial_assets.derivatives.option.option_factor import OptionFactor


class PortfolioCompanyShareOptionFactor(OptionFactor):
    """
    Factor for options whose underlying is a portfolio composed
    of company shares (equities).

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
            **kwargs,
        )
