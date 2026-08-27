from __future__ import annotations
from typing import Optional
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor


class BondFutureFactor(FutureFactor):
    """Base factor for bond futures (OHLCV price data)."""

    def __init__(
        self,
        name: str,
        group: str = "price",
        subgroup: Optional[str] = None,
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
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
