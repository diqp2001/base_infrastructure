"""
Factor definitions and parameters for Market Making SPX Call Spread Project
"""

from typing import Dict, List

from src.application.services.data.entities.factor.factor_library.finance.portfolio.company_share_portfolio import COMPANY_SHARE_PORTFOLIO_LIBRARY
from src.application.services.data.entities.factor.factor_library.finance.portfolio.portfolio_library import PORTFOLIO_LIBRARY
from src.application.services.data.entities.factor.factor_library.finance.financial_assets.derivatives.option.company_share_option_library import COMPANY_SHARE_OPTION_LIBRARY
from src.application.services.data.entities.factor.factor_library.finance.financial_assets.company_share_library import COMPANY_SHARE_LIBRARY
from src.application.services.data.entities.factor.factor_library.finance.financial_assets.derivatives.option.future_index_option_library import FUTURE_INDEX_OPTION_LIBRARY
from src.application.services.data.entities.factor.factor_library.finance.financial_assets.index_library import INDEX_LIBRARY
from src.application.services.data.entities.factor.factor_library.finance.financial_assets.derivatives.future.future_index_library import FUTURE_INDEX_LIBRARY


FACTOR_LIBRARY: Dict[str, Dict] = {
    "future_index_option_library": FUTURE_INDEX_OPTION_LIBRARY,
    "future_index_library": FUTURE_INDEX_LIBRARY,
    "index_library": INDEX_LIBRARY,
    "company_share_library":COMPANY_SHARE_LIBRARY,
    "company_share_portfolio_library":COMPANY_SHARE_PORTFOLIO_LIBRARY,
    "company_share_option_library":COMPANY_SHARE_OPTION_LIBRARY,

    "portfolio_library": PORTFOLIO_LIBRARY,
}


def get_factor_config(name: str) -> Dict:
    """
    Return definition & parameters for a given factor.
    """
    return FACTOR_LIBRARY.get(name, {})

