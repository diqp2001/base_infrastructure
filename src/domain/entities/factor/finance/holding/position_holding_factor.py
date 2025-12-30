from __future__ import annotations
from typing import Optional

from src.domain.entities.factor.finance.holding.holding_factor import HoldingFactor


class PositionHoldingFactor(HoldingFactor):
    """
    Domain entity representing a factor for any asset held inside a container
    with associated position information (LONG/SHORT and position reference).
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
        position_id: Optional[int] = None,
        position_type: Optional[str] = None,
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
        self.position_id = position_id
        self.position_type = position_type  # "LONG" or "SHORT"