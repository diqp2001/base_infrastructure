from datetime import date
from typing import Optional

from src.domain.entities.finance.financial_assets.derivatives.option.option import Option
from src.domain.entities.finance.financial_assets.derivatives.option.option_type import OptionType
from src.domain.entities.finance.portfolio.portfolio_company_share import PortfolioCompanyShare


class PortfolioCompanyShareOption(Option):
    """
    Option written on a company share.
    """

    

    def __init__(
            self,
            id: Optional[int],
            name: Optional[str],
            symbol: Optional[str],
            underlying_asset: PortfolioCompanyShare,
            option_type: OptionType,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            
        ):

        super().__init__(id =id,underlying_asset = underlying_asset, name=name, symbol=symbol, start_date=start_date, end_date=end_date,option_type = option_type)
    
    
        self.option_type = option_type

