

from datetime import timedelta
from typing import Dict, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_mid_price_factor import CompanyShareOptionMidPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_price_factor import CompanyShareOptionPriceFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_price_return_factor import CompanyShareOptionPriceReturnFactor


COMPANY_SHARE_OPTION_LIBRARY: Dict[str, Dict] = {
    
    "open": {
        "class": CompanyShareOptionFactor, 
        "name": "open",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level open price",
        "dependencies": [],
        "parameters": {}
    },
    "high": {
        "class": CompanyShareOptionFactor, 
        "name": "high",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level high price",
        "dependencies": [],
        "parameters": {}
    },
    "low": {
        "class": CompanyShareOptionFactor, 
        "name": "low",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level low price",
        "dependencies": [],
        "parameters": {}
    },
    "close": {
        "class": CompanyShareOptionFactor, 
        "name": "close",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level close price",
        "dependencies": [],
        "parameters": {}
    },
    "volume": {
        "class": CompanyShareOptionFactor, 
        "name": "volume",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level traded volume",
        "dependencies": [],
        "parameters": {}
    },
    "option_price": {
        "class": CompanyShareOptionPriceFactor,
        "name": "option_price",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level open price return",
        "dependencies": {
                        "close": {
                    "class": CompanyShareFactor,
                    "name": "close",
                    "group": "price",
                    "subgroup": "minutes",
                    "frequency": "1m",
                    "data_type": "numeric",
                    "description": "Minute-level close price",
                    "dependencies": {},
                    "parameters": {"independent_factor_related_entity_key":"underlying_asset_id"}
                },
                        "implied_volatility": {
                    "class": CompanyShareFactor, 
                    "name": "close",#needs to be close open volume or
                    "group": "implied_volatility",
                    "subgroup": "minutes",
                    "frequency": "1m",
                    "data_type": "numeric",
                    "description": "Minute-level open volatility",
                    "dependencies": [],
                    "parameters": {"independent_factor_related_entity_key":"underlying_asset_id"}
                },
                #         "yield": {
                #     "class": CompanyShareFactor, 
                #     "name": "implied_volatility",
                #     "group": "implied_volatility",
                #     "subgroup": "minutes",
                #     "frequency": "1m",
                #     "data_type": "numeric",
                #     "description": "Minute-level open volatility",
                #     "dependencies": [],
                #     "parameters": {"independent_factor_entity_id":"currency_id"}
                # },
        },
        "parameters": {}
    },
    "option_mid_price": {
        "class": CompanyShareOptionMidPriceFactor,
        "name": "option_mid_price",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level mid price return",
        "dependencies": {
                        "mid": {
                    "class": CompanyShareFactor,
                    "name": "mid",
                    "group": "price",
                    "subgroup": "minutes",
                    "frequency": "1m",
                    "data_type": "numeric",
                    "dependencies": {},
                    "parameters": {"independent_factor_related_entity_key":"underlying_asset_id"}
                },
                  
        },
        "parameters": {}
    },

    "return_open": {
        "class": CompanyShareOptionPriceReturnFactor, 
        "name": "return_open",
        "group": "return",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level open price return",
        "dependencies": {
            "start_price": {
                "class": CompanyShareOptionFactor,
                    "name": "open", 
                    "group": "price",
                    "subgroup": "minutes",
                    "data_type": "numeric",
                    "description": "Minute-level open price",
                    "dependencies": [],
                    "parameters": {"lag":timedelta(days=5, hours=3, minutes=10)}
                },
            "end_price": {
                "class": CompanyShareOptionFactor,
                    "name": "open", 
                    "group": "price",
                    "subgroup": "minutes",
                    "data_type": "numeric",
                    "description": "Minute-level open price",
                    "dependencies": [],
                    "parameters": {"lag":timedelta(days=4, hours=3, minutes=10)}
                },
                },
        "parameters": {}
    },
    
    # Daily return factors
    "return_daily": {
        "class": CompanyShareOptionPriceReturnFactor,
        "name": "return_daily",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Daily price return",
        "dependencies": {
            "start_price": {
                "class": CompanyShareOptionFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily close price",
                "dependencies": [],
                "parameters": {"lag": timedelta(days=2, hours=0, minutes=0)}
            },
            "end_price": {
                "class": CompanyShareOptionFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily close price",
                "dependencies": [],
                "parameters": {"lag": timedelta(days=1, hours=0, minutes=0)}
            }
        },
        "parameters": {"period": "1D"}
    },
    
    
    
}