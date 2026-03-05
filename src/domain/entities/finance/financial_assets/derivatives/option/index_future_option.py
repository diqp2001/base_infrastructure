"""
Index Future Option classes for options contracts on index futures.
Includes IndexFutureOption class that inherits from Option.
"""

from typing import Optional
from datetime import date
from decimal import Decimal
from .option import Option


class IndexFutureOption(Option):
    """
    Index Future Option domain entity.
    Represents options contracts on index futures (e.g., SPX, NDX, RUT options).
    Inherits from Option with additional properties specific to index futures.
    """
    def __init__(
            self,
            id: Optional[int],
            name: Optional[str],
            symbol: Optional[str],
            currency_id: Optional[int] = None,
            underlying_asset_id: Optional[int] = None,
            exchange_id: Optional[int] = None,
            option_type: Optional[str] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            strike_price: Optional[Decimal] = None,
            multiplier: Optional[int] = None,
            index_symbol: Optional[str] = None,
        ):

        super().__init__(
            id=id, 
            name=name, 
            symbol=symbol, 
            currency_id=currency_id,
            underlying_asset_id=underlying_asset_id,
            option_type=option_type,
            start_date=start_date, 
            end_date=end_date
        )
        self.strike_price = strike_price
        self.multiplier = multiplier  # Contract multiplier (e.g., 100 for SPX)
        self.index_symbol = index_symbol  # Underlying index symbol (e.g., SPX, NDX)
        self.exchange_id = exchange_id