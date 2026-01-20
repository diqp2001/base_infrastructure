from datetime import date
from typing import Optional

from src.domain.entities.finance.financial_assets.derivatives.option.option import Option
from src.domain.entities.finance.financial_assets.derivatives.option.option_type import OptionType


class PortfolioCompanyShareOption(Option):
    """
    Option written on a company share.
    """

    def __init__(
            self,
            id: Optional[int],
            name: Optional[str],
            symbol: Optional[str],
            currency_id: Optional[int] = None,
            underlying_asset_id: Optional[int] = None,
            option_type: Optional[OptionType] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            
        ):

        super().__init__(id=id, currency_id=currency_id, underlying_asset_id=underlying_asset_id, name=name, symbol=symbol, start_date=start_date, end_date=end_date, option_type=option_type)

