from datetime import date
from typing import Optional
from src.domain.entities.finance.financial_assets.derivatives.derivative import Derivative


class Forward(Derivative):
    """
    Forward contract with currency and underlying asset references.
    """

    def __init__(
            self,
            id: Optional[int],
            name: Optional[str],
            symbol: Optional[str],
            currency_id: Optional[int] = None,
            underlying_asset_id: Optional[int] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            
        ):

        super().__init__(id=id, underlying_asset_id=underlying_asset_id, name=name, symbol=symbol, start_date=start_date, end_date=end_date)
        self.currency_id = currency_id
    
