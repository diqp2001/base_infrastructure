from datetime import date
from typing import Optional
from src.domain.entities.finance.financial_assets.derivatives.derivative import Derivative
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class Forward(Derivative):
    """
    Futures contract with exchange link.
    """

    def __init__(
            self,
            id: Optional[int],
            name: Optional[str],
            symbol: Optional[str],
            underlying_asset: FinancialAsset,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            
        ):

        super().__init__(id =id,underlying_asset = underlying_asset, name=name, symbol=symbol, start_date=start_date, end_date=end_date)
    
