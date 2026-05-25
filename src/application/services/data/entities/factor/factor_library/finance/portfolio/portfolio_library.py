from datetime import timedelta
from typing import Dict, List

from src.domain.entities.factor.finance.holding.portfolio_holding_value_factor import PortfolioHoldingValueFactor
from src.domain.entities.factor.finance.portfolio.portfolio_value_factor import PortfolioValueFactor
from src.domain.entities.factor.finance.portfolio.portfolio_factor import PortfolioFactor




PORTFOLIO_LIBRARY: Dict[str, Dict] = {

    # "volume": {
    #     "class": PortfolioFactor,
    #     "name": "volume",
    #     "group": "price",
    #     "subgroup": "minutes",
    #     "frequency": "1m",
    #     "data_type": "numeric",
    #     "description": "Minute-level traded volume",
    #     "dependencies": {},
    #     "parameters": {}
    # },

    "portfolio_value": {
        "class": PortfolioValueFactor,
        "name": "portfolio_value",
        "group": "value",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Daily value of the portfolio calculated from holding values",
        "dependencies": {
            "holding_value": {
                "class": PortfolioHoldingValueFactor,
                "name": "holding_value",
                "group": "value",
                "subgroup": "daily",
                "frequency": "1d",
                "data_type": "numeric",
                "description": "Daily value of each holding in the portfolio",
                "dependencies": {
                
                        "holding_value": {
                        "class": PortfolioHoldingValueFactor,
                        "name": "holding_value",
                        "group": "value",
                        "subgroup": "daily",
                        "frequency": "1d",
                        "data_type": "numeric",
                        "description": "Daily value of each holding in the portfolio",
                        "dependencies": {},
                        "parameters": {}
                    }
            },
                "parameters": {}
            }
        },
        "parameters": {"period": "1D"}
    },
    # ======================
    # Daily Return Factors
    # ======================

    # "return_daily": {
    #     "class": CompanySharePriceReturnFactor,
    #     "name": "return_daily",
    #     "group": "return",
    #     "subgroup": "daily",
    #     "frequency": "1d",
    #     "data_type": "numeric",
    #     "description": "Daily price return",
    #     "dependencies": {
    #         "start_price": {
    #             "class": CompanyShareFactor,
    #             "name": "close",
    #             "group": "price",
    #             "subgroup": "daily",
    #             "data_type": "numeric",
    #             "description": "Daily close price",
    #             "dependencies": {},
    #             "parameters": {"lag": timedelta(days=2, hours=0, minutes=0)}
    #         },
    #         "end_price": {
    #             "class": CompanyShareFactor,
    #             "name": "close",
    #             "group": "price",
    #             "subgroup": "daily",
    #             "data_type": "numeric",
    #             "description": "Daily close price",
    #             "dependencies": {},
    #             "parameters": {"lag": timedelta(days=1, hours=0, minutes=0)}
    #         }
    #     },
    #     "parameters": {"period": "1D"}
    # },
    # "return_daily_3": {
    #     "class": CompanySharePriceReturnFactor,
    #     "name": "return_daily",
    #     "group": "return",
    #     "subgroup": "daily",
    #     "frequency": "1d",
    #     "data_type": "numeric",
    #     "description": "Daily price return",
    #     "dependencies": {
    #         "start_price": {
    #             "class": CompanyShareFactor,
    #             "name": "close",
    #             "group": "price",
    #             "subgroup": "daily",
    #             "data_type": "numeric",
    #             "description": "Daily close price",
    #             "dependencies": {},
    #             "parameters": {"lag": timedelta(days=5, hours=0, minutes=0)}
    #         },
    #         "end_price": {
    #             "class": CompanyShareFactor,
    #             "name": "close",
    #             "group": "price",
    #             "subgroup": "daily",
    #             "data_type": "numeric",
    #             "description": "Daily close price",
    #             "dependencies": {},
    #             "parameters": {"lag": timedelta(days=1, hours=0, minutes=0)}
    #         }
    #     },
    #     "parameters": {"period": "1D"}
    # },

    
}
