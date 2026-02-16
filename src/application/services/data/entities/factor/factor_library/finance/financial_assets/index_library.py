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
    
}