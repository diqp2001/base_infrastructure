from datetime import timedelta
from typing import Dict, List

from src.domain.entities.factor.finance.financial_assets.index.index_factor import IndexFactor
from src.domain.entities.factor.finance.financial_assets.index.index_price_return_factor import IndexPriceReturnFactor

INDEX_LIBRARY: Dict[str, Dict] = {
    


    # ======================
    # Minute Price Factors
    # ======================

    "open": {
        "class": IndexFactor,
        "name": "open",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level open price",
        "dependencies": {},
        "parameters": {}
    },

    "high": {
        "class": IndexFactor,
        "name": "high",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level high price",
        "dependencies": {},
        "parameters": {}
    },

    "low": {
        "class": IndexFactor,
        "name": "low",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level low price",
        "dependencies": {},
        "parameters": {}
    },

    "close": {
        "class": IndexFactor,
        "name": "close",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level close price",
        "dependencies": {},
        "parameters": {}
    },

    "volume": {
        "class": IndexFactor,
        "name": "volume",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level traded volume",
        "dependencies": {},
        "parameters": {}
    },

    # ======================
    # Minute Return Factors
    # ======================

    "return_open": {
        "class": IndexPriceReturnFactor,
        "name": "return_open",
        "group": "return",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level open price return",
        "dependencies": {
            "start_price": {
                "class": IndexFactor,
                "name": "open",
                "group": "price",
                "subgroup": "minutes",
                "data_type": "numeric",
                "description": "Minute-level open price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=1, hours=0, minutes=0)}
            },
            "end_price": {
                "class": IndexFactor,
                "name": "open",
                "group": "price",
                "subgroup": "minutes",
                "data_type": "numeric",
                "description": "Minute-level open price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=0, hours=0, minutes=1)}
            }
        },
        "parameters": {}
    },

    # ======================
    # Daily Return Factors
    # ======================

    "return_daily": {
        "class": IndexPriceReturnFactor,
        "name": "return_daily",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Daily price return",
        "dependencies": {
            "start_price": {
                "class": IndexFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily close price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=2, hours=0, minutes=0)}
            },
            "end_price": {
                "class": IndexFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily close price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=1, hours=0, minutes=0)}
            }
        },
        "parameters": {"period": "1D"}
    },

    # ======================
    # Weekly Return Factors
    # ======================

    "return_weekly": {
        "class": IndexPriceReturnFactor,
        "name": "return_weekly",
        "group": "return",
        "subgroup": "weekly",
        "frequency": "1w",
        "data_type": "numeric",
        "description": "Weekly price return",
        "dependencies": {
            "start_price": {
                "class": IndexFactor,
                "name": "close",
                "group": "price",
                "subgroup": "weekly",
                "data_type": "numeric",
                "description": "Weekly close price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=14, hours=0, minutes=0)}
            },
            "end_price": {
                "class": IndexFactor,
                "name": "close",
                "group": "price",
                "subgroup": "weekly",
                "data_type": "numeric",
                "description": "Weekly close price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=7, hours=0, minutes=0)}
            }
        },
        "parameters": {"period": "1W"}
    },

    # ======================
    # Monthly Return Factors
    # ======================

    "return_monthly": {
        "class": IndexPriceReturnFactor,
        "name": "return_monthly",
        "group": "return",
        "subgroup": "monthly",
        "frequency": "1mth",
        "data_type": "numeric",
        "description": "Monthly price return",
        "dependencies": {
            "start_price": {
                "class": IndexFactor,
                "name": "close",
                "group": "price",
                "subgroup": "monthly",
                "data_type": "numeric",
                "description": "Monthly close price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=60, hours=0, minutes=0)}
            },
            "end_price": {
                "class": IndexFactor,
                "name": "close",
                "group": "price",
                "subgroup": "monthly",
                "data_type": "numeric",
                "description": "Monthly close price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=30, hours=0, minutes=0)}
            }
        },
        "parameters": {"period": "1M"}
    },
}

    
