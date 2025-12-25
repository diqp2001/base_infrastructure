from datetime import date
from typing import Optional

from src.domain.entities.finance.financial_assets.derivatives.option.option import Option
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.financial_assets.derivatives.option.option_type import OptionType


class CompanyShareOption(Option):
    """
    Option written on a company share.
    """

    def __init__(self,
                 id: int,
                 underlying_share: CompanyShare,
                 expiration_date: date,
                 option_type: OptionType,
                 start_date: date,
                 end_date: Optional[date] = None):


        super().__init__(
            id=id,
            underlying_asset=underlying_share,
            expiration_date=expiration_date,
            option_type=option_type,
            start_date=start_date,
            end_date=end_date
        )
