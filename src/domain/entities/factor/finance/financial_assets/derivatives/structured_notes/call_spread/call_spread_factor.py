from __future__ import annotations
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.structured_notes.structured_note_factor import StructuredNoteFactor





class CallSpreadFactor(StructuredNoteFactor):
    """Domain entity representing a derivative-specific factor."""

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
