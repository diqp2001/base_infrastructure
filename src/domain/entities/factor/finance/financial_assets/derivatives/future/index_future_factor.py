from __future__ import annotations
from typing import Optional
from datetime import timedelta
import math

from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor


class IndexFutureFactor(FutureFactor):
    """Domain factor representing index future-specific characteristics."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        underlying_index: Optional[str] = None,
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
        self.underlying_index = underlying_index