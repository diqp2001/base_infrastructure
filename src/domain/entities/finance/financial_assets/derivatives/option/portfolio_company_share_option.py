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
                 company_id: int,
                 expiration_date: date,
                 option_type: OptionType,
                 exercise_style: str,
                 strike_id: Optional[int],
                 start_date: date,
                 end_date: Optional[date] = None):

        self.company_id = company_id

        super().__init__(
            id=id,
            underlying_asset=underlying,
            expiration_date=expiration_date,
            option_type=option_type,
            exercise_style=exercise_style,
            strike_id=strike_id,
            start_date=start_date,
            end_date=end_date
        )
