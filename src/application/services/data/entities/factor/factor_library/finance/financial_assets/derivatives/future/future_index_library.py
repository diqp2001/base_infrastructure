from datetime import timedelta
from typing import Dict, List

from src.domain.entities.factor.finance.financial_assets.derivatives.future.index_future_price_return_factor import IndexFuturePriceReturnFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.future.index_future_factor import IndexFutureFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_price_return_factor import FuturePriceReturnFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_annualized_price_return_factor import FutureAnnualizedPriceReturnFactor

FUTURE_INDEX_LIBRARY: Dict[str, Dict] = {
    
"open": {
        "class": IndexFutureFactor, 
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
        "class": IndexFutureFactor, 
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
        "class": IndexFutureFactor, 
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
        "class": IndexFutureFactor, 
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
        "class": IndexFutureFactor, 
        "name": "volume",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level traded volume",
        "dependencies": [],
        "parameters": {}
    },

    "return_open": {
        "class": IndexFuturePriceReturnFactor, 
        "name": "return_open",
        "group": "return",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level open price return",
        "dependencies": {
            "start_price": {
                "class": IndexFutureFactor,
                    "name": "open", 
                    "group": "price",
                    "subgroup": "minutes",
                    "data_type": "numeric",
                    "description": "Minute-level open price",
                    "dependencies": [],
                    "parameters": {"lag":timedelta(days=5, hours=3, minutes=10)}
                },
            "end_price": {
                "class": IndexFutureFactor,
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
        "class": IndexFuturePriceReturnFactor,
        "name": "return_daily",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Daily price return",
        "dependencies": {
            "start_price": {
                "class": IndexFutureFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily close price",
                "dependencies": [],
                "parameters": {"lag": timedelta(days=2, hours=0, minutes=0)}
            },
            "end_price": {
                "class": IndexFutureFactor,
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
    
    # Weekly return factors
    "return_weekly": {
        "class": IndexFuturePriceReturnFactor,
        "name": "return_weekly",
        "group": "return",
        "subgroup": "weekly",
        "frequency": "1w",
        "data_type": "numeric",
        "description": "Weekly price return",
        "dependencies": {
            "start_price": {
                "class": IndexFutureFactor,
                "name": "close",
                "group": "price",
                "subgroup": "weekly",
                "data_type": "numeric",
                "description": "Weekly close price",
                "dependencies": [],
                "parameters": {"lag": timedelta(days=14, hours=0, minutes=0)}
            },
            "end_price": {
                "class": IndexFutureFactor,
                "name": "close",
                "group": "price",
                "subgroup": "weekly",
                "data_type": "numeric",
                "description": "Weekly close price",
                "dependencies": [],
                "parameters": {"lag": timedelta(days=7, hours=0, minutes=0)}
            }
        },
        "parameters": {"period": "1W"}
    },
    
    # Monthly return factors
    "return_monthly": {
        "class": IndexFuturePriceReturnFactor,
        "name": "return_monthly",
        "group": "return",
        "subgroup": "monthly",
        "frequency": "1mth",
        "data_type": "numeric",
        "description": "Monthly price return",
        "dependencies": {
            "start_price": {
                "class": IndexFutureFactor,
                "name": "close",
                "group": "price",
                "subgroup": "monthly",
                "data_type": "numeric",
                "description": "Monthly close price",
                "dependencies": [],
                "parameters": {"lag": timedelta(days=60, hours=0, minutes=0)}
            },
            "end_price": {
                "class": IndexFutureFactor,
                "name": "close",
                "group": "price",
                "subgroup": "monthly",
                "data_type": "numeric",
                "description": "Monthly close price",
                "dependencies": [],
                "parameters": {"lag": timedelta(days=30, hours=0, minutes=0)}
            }
        },
        "parameters": {"period": "1M"}
    },
    
}