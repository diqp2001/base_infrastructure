from __future__ import annotations
from domain.entities.factor.factor import Factor



from decimal import Decimal
from typing import Optional

class FinancialAssetFactor(Factor):

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = "numeric",
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
    ):
        super().__init__(name, group, subgroup, data_type, source, definition, factor_id)

