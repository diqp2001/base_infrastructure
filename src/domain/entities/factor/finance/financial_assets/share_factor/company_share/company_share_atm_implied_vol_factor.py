"""
CompanyShareATMImpliedVolFactor — ATM implied volatility for a company share.

Represents the implied volatility surface at-the-money (strike ≈ spot price)
for a given underlying company share. Fetched directly from IBKR option chain data.
"""

from __future__ import annotations
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor


class CompanyShareATMImpliedVolFactor(CompanyShareFactor):
    """
    Domain entity representing the at-the-money implied volatility of a company share.

    This is a leaf factor resolved via IBKR (Branch B). No calculate_dependencies
    are declared; the value is fetched directly from IBKR option market data.
    """

    def __init__(
        self,
        name: str = "atm_implied_vol",
        group: str = "volatility",
        subgroup: Optional[str] = "implied",
        frequency: Optional[str] = "1d",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "ibkr",
        definition: Optional[str] = "At-the-money implied volatility derived from IBKR option chain",
        factor_id: Optional[int] = None,
        **kwargs,
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
            **kwargs,
        )

    def __repr__(self):
        return (
            f"CompanyShareATMImpliedVolFactor(name={self.name!r}, group={self.group!r}, "
            f"subgroup={self.subgroup!r})"
        )
