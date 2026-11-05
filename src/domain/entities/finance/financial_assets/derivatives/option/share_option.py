from datetime import date
from typing import Optional
from decimal import Decimal

from src.domain.entities.finance.financial_assets.derivatives.option.option import Option


class ShareOption(Option):
    """
    Listed option written on a share (a company share or an ETF share): the contract terms common to both.
    Identification only; greeks, IV and prices live in factors.
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
            expiry: Optional[str] = None,
        ):
        super().__init__(id=id, currency_id=currency_id, underlying_asset_id=underlying_asset_id, name=name, symbol=symbol, start_date=start_date, end_date=end_date, option_type=option_type)
        self.strike_price = strike_price
        self.multiplier = multiplier  # Contract multiplier (100 for a standard US equity / ETF option)
        self.exchange_id = exchange_id
        self.expiry = expiry
