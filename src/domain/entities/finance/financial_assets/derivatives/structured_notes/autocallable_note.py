from __future__ import annotations
from typing import List, Optional
from datetime import date
from decimal import Decimal

from domain.entities.finance.financial_assets.derivatives.derivative_leg import DerivativeLeg
from domain.entities.finance.financial_assets.derivatives.structured_notes.structured_note import StructuredNote
from domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class AutocallableNote(StructuredNote):
    """
    Identification-only Autocallable Note.

    Pricing, payoff, Greeks, replication live in factors/services.
    """

    def __init__(
        self,
        id: int,
        underlying_asset: FinancialAsset,
        legs: List[DerivativeLeg],
        start_date: date,
        maturity_date: date,
        end_date: Optional[date] = None,
    ):
        super().__init__(
            id=id,
            underlying_asset=underlying_asset,
            legs=legs,
            start_date=start_date,
            end_date=end_date or maturity_date,
        )

        self.maturity_date = maturity_date
