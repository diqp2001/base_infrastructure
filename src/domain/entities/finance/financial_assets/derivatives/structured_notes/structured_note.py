from __future__ import annotations
from typing import List, Optional
from datetime import date

from domain.entities.finance.financial_assets.derivatives.derivative import Derivative
from domain.entities.finance.financial_assets.derivatives.derivative_leg import DerivativeLeg
from domain.entities.finance.financial_assets.financial_asset import FinancialAsset



class StructuredNote(Derivative):
    """
    Identification-only structured note.

    Payoff logic lives in factors/services.
    """

    def __init__(
        self,
        id: int,
        underlying_asset: FinancialAsset,
        legs: List[DerivativeLeg],
        start_date: date,
        end_date: Optional[date] = None,
    ):
        super().__init__(id, underlying_asset, start_date, end_date)

        self.legs = legs
