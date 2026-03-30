"""
Factor definitions and parameters for Market Making SPX Call Spread Project
"""

from typing import Dict, List

from src.application.services.data.entities.factor.factor_library.finance.financial_assets.derivatives.option.company_share_option_library import COMPANY_SHARE_OPTION_LIBRARY
from src.application.services.data.entities.factor.factor_library.finance.financial_assets.company_share_library import COMPANY_SHARE_LIBRARY
from src.application.services.data.entities.factor.factor_library.finance.financial_assets.derivatives.option.future_index_option_library import FUTURE_INDEX_OPTION_LIBRARY
from src.application.services.data.entities.factor.factor_library.finance.financial_assets.index_library import INDEX_LIBRARY
from src.application.services.data.entities.factor.factor_library.finance.financial_assets.derivatives.future.future_index_library import FUTURE_INDEX_LIBRARY

# Technical indicators library
TECHNICAL_LIBRARY: Dict[str, Dict] = {
    "sma_10": {
        "group": "technical",
        "subgroup": "trend",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Simple Moving Average (10 periods)",
        "dependencies": ["close"],
        "parameters": {"period": 10}
    },
    "sma_20": {
        "group": "technical",
        "subgroup": "trend",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Simple Moving Average (20 periods)",
        "dependencies": ["close"],
        "parameters": {"period": 20}
    },
    "rsi": {
        "group": "technical",
        "subgroup": "momentum",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Relative Strength Index",
        "dependencies": ["close"],
        "parameters": {"period": 14}
    },
    "macd": {
        "group": "technical",
        "subgroup": "momentum",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "MACD indicator",
        "dependencies": ["close"],
        "parameters": {"fast_period": 12, "slow_period": 26, "signal_period": 9}
    },
    "bb_upper": {
        "group": "technical",
        "subgroup": "volatility",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Upper Bollinger Band",
        "dependencies": ["close"],
        "parameters": {"period": 20, "std_dev_multiplier": 2}
    },
    "bb_lower": {
        "group": "technical",
        "subgroup": "volatility",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Lower Bollinger Band",
        "dependencies": ["close"],
        "parameters": {"period": 20, "std_dev_multiplier": 2}
    },
}

# Volatility factors library
VOLATILITY_LIBRARY: Dict[str, Dict] = {
    "realized_vol_10": {
        "group": "volatility",
        "subgroup": "realized",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Realized volatility over 10 periods",
        "dependencies": ["close"],
        "parameters": {"lookback": 10}
    },
    "realized_vol_20": {
        "group": "volatility",
        "subgroup": "realized",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Realized volatility over 20 periods",
        "dependencies": ["close"],
        "parameters": {"lookback": 20}
    },
    "vix": {
        "group": "volatility",
        "subgroup": "implied",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "VIX (implied volatility index)",
        "dependencies": [],
        "parameters": {}
    },
    "term_structure": {
        "group": "volatility",
        "subgroup": "term_structure",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Volatility term structure",
        "dependencies": [],
        "parameters": {}
    },
}

# Market factors library
MARKET_LIBRARY: Dict[str, Dict] = {
    "put_call_ratio": {
        "group": "market",
        "subgroup": "sentiment",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Put/Call ratio",
        "dependencies": [],
        "parameters": {}
    },
    "skew": {
        "group": "market",
        "subgroup": "options",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Options skew",
        "dependencies": [],
        "parameters": {}
    },
    "term_structure_slope": {
        "group": "market",
        "subgroup": "rates",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Term structure slope",
        "dependencies": [],
        "parameters": {}
    },
}

FACTOR_LIBRARY: Dict[str, Dict] = {
    "future_index_option_library": FUTURE_INDEX_OPTION_LIBRARY,
    "future_index_library": FUTURE_INDEX_LIBRARY,
    "index_library": INDEX_LIBRARY,
    "company_share_library":COMPANY_SHARE_LIBRARY,
    "company_share_option_library":COMPANY_SHARE_OPTION_LIBRARY,
    "technical_library": TECHNICAL_LIBRARY,
    "volatility_library": VOLATILITY_LIBRARY,
    "market_library": MARKET_LIBRARY,
}


def get_factor_config(name: str) -> Dict:
    """
    Return definition & parameters for a given factor.
    """
    return FACTOR_LIBRARY.get(name, {})

