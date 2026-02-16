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
        "group": "return",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level open price return",
        "dependencies": {
            "open": {
                "class": FutureFactor, 
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
}