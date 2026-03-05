from decimal import Decimal
from datetime import date

from src.domain.entities.finance.financial_assets.derivatives.derivative_leg import DerivativeLeg
from src.domain.entities.finance.financial_assets.derivatives.option.option import Option
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset

from .structured_note import StructuredNote


class CallSpreadNote(StructuredNote):
    """
    Structured note containing a call spread (long call + short call).
    """

    def __init__(
        self,
        id: int,
        underlying_asset: FinancialAsset,
        long_call: Option,
        short_call: Option,
        start_date: date,
        end_date: date,
    ):
        

        legs = [
            DerivativeLeg(long_call, Decimal("1")),
            DerivativeLeg(short_call, Decimal("-1")),
        ]

        super().__init__(
            id=id,
            underlying_asset=underlying_asset,
            legs=legs,
            start_date=start_date,
            end_date=end_date,
        )
