from __future__ import annotations
import math
from typing import Optional, Union
from datetime import timedelta

from src.domain.entities.factor.finance.financial_assets.derivatives.derivative_factor import DerivativeFactor



class OptionFactor(DerivativeFactor):
    """Domain factor representing general option-specific characteristics."""

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

    