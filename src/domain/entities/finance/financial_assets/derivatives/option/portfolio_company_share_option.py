from datetime import date
from typing import Optional

from domain.entities.finance.financial_assets.derivatives.option.option import Option
from domain.entities.finance.financial_assets.derivatives.option.option_type import OptionType
from domain.entities.finance.portfolio.portfolio_company_share import PortfolioCompanyShare


class PortfolioCompanyShareOption(Option):
    """
    Option written on a company share.
    """

    def __init__(self,
                 id: int,
                 underlying: PortfolioCompanyShare,
                 expiration_date: date,
                 option_type: OptionType,
                 start_date: date,
                 end_date: Optional[date] = None):


        super().__init__(
            id=id,
            underlying_asset=underlying,
            expiration_date=expiration_date,
            option_type=option_type,
            start_date=start_date,
            end_date=end_date
        )
