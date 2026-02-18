from typing import Dict, List

from src.domain.entities.factor.finance.financial_assets.index.index_factor import IndexFactor
from src.domain.entities.factor.finance.financial_assets.index.index_price_return_factor import IndexPriceReturnFactor

INDEX_LIBRARY: Dict[str, Dict] = {
    
"open": {
        "class": IndexFactor, 
        "group": "price",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level open price",
        "dependencies": [],
        "parameters": {}
    },
    "high": {
        "class": IndexFactor, 
        "group": "price",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level high price",
        "dependencies": [],
        "parameters": {}
    },
    "low": {
        "class": IndexFactor, 
        "group": "price",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level low price",
        "dependencies": [],
        "parameters": {}
    },
    "close": {
        "class": IndexFactor, 
        "group": "price",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level close price",
        "dependencies": [],
        "parameters": {}
    },
    "volume": {
        "class": IndexFactor, 
        "group": "price",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level traded volume",
        "dependencies": [],
        "parameters": {}
    },
    "return_open": {
        "class": IndexPriceReturnFactor, 
        "group": "return",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level open price return",
        "dependencies": {
            "open": {
                "class": IndexFactor, 
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
        "class": IndexPriceReturnFactor,
        "group": "return",
        "subgroup": "daily",
        "data_type": "numeric",
        "description": "Daily price return",
        "dependencies": {
            "close": {
                "class": IndexFactor,
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
        "class": IndexPriceReturnFactor,
        "group": "return",
        "subgroup": "weekly",
        "data_type": "numeric",
        "description": "Weekly price return",
        "dependencies": {
            "close": {
                "class": IndexFactor,
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
        "class": IndexPriceReturnFactor,
        "group": "return",
        "subgroup": "monthly",
        "data_type": "numeric",
        "description": "Monthly price return",
        "dependencies": {
            "close": {
                "class": IndexFactor,
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