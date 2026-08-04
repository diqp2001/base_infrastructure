


from datetime import timedelta
from typing import Dict

from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_equal_weight_return_factor import CompanySharePortfolioEqualWeightReturnFactor
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_price_return_factor import CompanySharePortfolioPriceReturnFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_price_return_factor import CompanySharePriceReturnFactor
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_factor import CompanySharePortfolioFactor


COMPANY_SHARE_PORTFOLIO_LIBRARY: Dict[str, Dict] = {

    
    "return_daily_3": {
        "class": CompanySharePortfolioPriceReturnFactor,
        "name": "return_daily",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Daily price return",
        "dependencies": {
            "start_price": {
                "class": CompanySharePortfolioFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "frequency": "1d",
                "data_type": "numeric",
                "description": "Daily close price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=5, hours=0, minutes=0)}
            },
            "end_price": {
                "class": CompanySharePortfolioFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "frequency": "1d",
                "data_type": "numeric",
                "description": "Daily close price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=1, hours=0, minutes=0)}
            }
        },
        "parameters": {"period": "1D"}
    },

        "return_eq_w_daily_3": {
        "class": CompanySharePortfolioEqualWeightReturnFactor,
        "name": "return_daily",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Daily price return",
        "dependencies": {
            "CompanySharePriceReturnFactor": {
                "class": CompanySharePriceReturnFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "frequency": "1d",
                "data_type": "numeric",
                "description": "Daily close price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=5, hours=0, minutes=0)}
            },
            
        },
        "parameters": {"period": "1D"}
    },

    
   
}
