from typing import Dict, List

from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_price_return_factor import FuturePriceReturnFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_annualized_price_return_factor import FutureAnnualizedPriceReturnFactor

FUTURE_INDEX_LIBRARY: Dict[str, Dict] = {
    
"open": {
        "class": FutureFactor, 
        "group": "price",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level open price",
        "dependencies": [],
        "parameters": {}
    },
    "high": {
        "class": FutureFactor, 
        "group": "price",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level high price",
        "dependencies": [],
        "parameters": {}
    },
    "low": {
        "class": FutureFactor, 
        "group": "price",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level low price",
        "dependencies": [],
        "parameters": {}
    },
    "close": {
        "class": FutureFactor, 
        "group": "price",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level close price",
        "dependencies": [],
        "parameters": {}
    },
    "volume": {
        "class": FutureFactor, 
        "group": "price",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level traded volume",
        "dependencies": [],
        "parameters": {}
    },

    "return_open": {
        "class": FuturePriceReturnFactor, 
        "name": "return_open",
        "group": "return",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level open price return",
        "dependencies": {
            "open": {
                "class": FutureFactor,
                    "name": "open", 
                    "group": "price",
                    "subgroup": "minutes",
                    "data_type": "numeric",
                    "description": "Minute-level open price",
                    "dependencies": [],
                    "parameters": {}
                },
                },
        "parameters": {}
    },
    
    # Daily return factors
    "return_daily": {
        "class": FuturePriceReturnFactor,
        "name": "return_daily",
        "group": "return",
        "subgroup": "daily",
        "data_type": "numeric",
        "description": "Daily price return",
        "dependencies": {
            "close": {
                "class": FutureFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily close price",
                "dependencies": [],
                "parameters": {}
            },
        },
        "parameters": {"period": "1D"}
    },
    
    # Weekly return factors
    "return_weekly": {
        "class": FuturePriceReturnFactor,
        "name": "return_weekly",
        "group": "return",
        "subgroup": "weekly",
        "data_type": "numeric",
        "description": "Weekly price return",
        "dependencies": {
            "close": {
                "class": FutureFactor,
                "name": "close",
                "group": "price",
                "subgroup": "weekly",
                "data_type": "numeric",
                "description": "Weekly close price",
                "dependencies": [],
                "parameters": {}
            },
        },
        "parameters": {"period": "1W"}
    },
    
    # Monthly return factors
    "return_monthly": {
        "class": FuturePriceReturnFactor,
        "name": "return_monthly",
        "group": "return",
        "subgroup": "monthly",
        "data_type": "numeric",
        "description": "Monthly price return",
        "dependencies": {
            "close": {
                "class": FutureFactor,
                "name": "close",
                "group": "price",
                "subgroup": "monthly",
                "data_type": "numeric",
                "description": "Monthly close price",
                "dependencies": [],
                "parameters": {}
            },
        },
        "parameters": {"period": "1M"}
    },
    
}