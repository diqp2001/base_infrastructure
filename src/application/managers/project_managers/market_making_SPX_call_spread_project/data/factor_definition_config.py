"""
Factor definitions and parameters for Market Making SPX Call Spread Project
"""

from typing import Dict, List

FACTOR_LIBRARY: Dict[str, Dict] = {
    # --------------------------
    # Price-based factors
    # --------------------------
    "open": {
        "group": "price",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level open price",
        "dependencies": [],
        "parameters": {}
    },
    "high": {
        "group": "price",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level high price",
        "dependencies": [],
        "parameters": {}
    },
    "low": {
        "group": "price",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level low price",
        "dependencies": [],
        "parameters": {}
    },
    "close": {
        "group": "price",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level close price",
        "dependencies": [],
        "parameters": {}
    },
    "volume": {
        "group": "price",
        "subgroup": "minutes",
        "data_type": "numeric",
        "description": "Minute-level traded volume",
        "dependencies": [],
        "parameters": {}
    },

    # --------------------------
    # Technical indicators
    # --------------------------
    "sma_10": {
        "group": "technical",
        "subgroup": "trend",
        "data_type": "numeric",
        "description": "Simple Moving Average (10 periods)",
        "dependencies": ["close"],
        "parameters": {
            "period": 10
        }
    },
    "sma_20": {
        "group": "technical",
        "subgroup": "trend",
        "data_type": "numeric",
        "description": "Simple Moving Average (20 periods)",
        "dependencies": ["close"],
        "parameters": {
            "period": 20
        }
    },
    "rsi": {
        "group": "technical",
        "subgroup": "momentum",
        "data_type": "numeric",
        "description": "Relative Strength Index",
        "dependencies": ["close"],
        "parameters": {
            "period": 14
        }
    },
    "macd": {
        "group": "technical",
        "subgroup": "momentum",
        "data_type": "numeric",
        "description": "MACD indicator",
        "dependencies": ["close"],
        "parameters": {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9
        }
    },
    "bb_upper": {
        "group": "technical",
        "subgroup": "volatility",
        "data_type": "numeric",
        "description": "Upper Bollinger Band",
        "dependencies": ["close"],
        "parameters": {
            "period": 20,
            "std_dev_multiplier": 2
        }
    },
    "bb_lower": {
        "group": "technical",
        "subgroup": "volatility",
        "data_type": "numeric",
        "description": "Lower Bollinger Band",
        "dependencies": ["close"],
        "parameters": {
            "period": 20,
            "std_dev_multiplier": 2
        }
    },

    # --------------------------
    # Volatility measures
    # --------------------------
    "realized_vol_10": {
        "group": "volatility",
        "subgroup": "realized",
        "data_type": "numeric",
        "description": "Realized volatility over 10 periods",
        "dependencies": ["close"],
        "parameters": {
            "lookback": 10
        }
    },
    "realized_vol_20": {
        "group": "volatility",
        "subgroup": "realized",
        "data_type": "numeric",
        "description": "Realized volatility over 20 periods",
        "dependencies": ["close"],
        "parameters": {
            "lookback": 20
        }
    },
    "vix": {
        "group": "volatility",
        "subgroup": "implied",
        "data_type": "numeric",
        "description": "VIX (implied volatility index)",
        "dependencies": [],
        "parameters": {}
    },
    "term_structure": {
        "group": "volatility",
        "subgroup": "term_structure",
        "data_type": "numeric",
        "description": "Volatility term structure",
        "dependencies": [],
        "parameters": {}
    },

    # --------------------------
    # Market-wide factors
    # --------------------------
    "put_call_ratio": {
        "group": "market",
        "subgroup": "sentiment",
        "data_type": "numeric",
        "description": "Put/Call ratio",
        "dependencies": [],
        "parameters": {}
    },
    "skew": {
        "group": "market",
        "subgroup": "options",
        "data_type": "numeric",
        "description": "Options skew",
        "dependencies": [],
        "parameters": {}
    },
    "term_structure_slope": {
        "group": "market",
        "subgroup": "rates",
        "data_type": "numeric",
        "description": "Term structure slope",
        "dependencies": [],
        "parameters": {}
    }
}


def get_factor_config(name: str) -> Dict:
    """
    Return definition & parameters for a given factor.
    """
    return FACTOR_LIBRARY.get(name, {})
