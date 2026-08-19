from typing import Dict

from src.domain.entities.factor.finance.financial_assets.currency.currency_value_factor import CurrencyValueFactor
from src.domain.entities.factor.finance.financial_assets.currency.currency_rate_factor import CurrencyRateFactor
from src.domain.entities.factor.finance.financial_assets.currency.currency_yield_factor import CurrencyYieldFactor


CURRENCY_LIBRARY: Dict[str, Dict] = {

    "currency_value": {
        "class": CurrencyValueFactor,
        "name": "currency_value",
        "group": "value",
        "subgroup": "asset",
        "frequency": "1d",
        "data_type": "decimal",
        "description": "Market value of a currency asset, derived from mid price",
        "dependencies": {
            "currency_mid_price_factor": {
                "class": CurrencyRateFactor,
                "name": "mid_price",
                "group": "price",
                "subgroup": "mid_price_true",
                "frequency": "1d",
                "data_type": "decimal",
                "description": "Mid exchange rate of the currency",
                "dependencies": {},
                "parameters": {}
            }
        },
        "parameters": {}
    },

    "currency_rate": {
        "class": CurrencyRateFactor,
        "name": "mid_price",
        "group": "price",
        "subgroup": "mid_price_true",
        "frequency": "1d",
        "data_type": "decimal",
        "description": "True mid exchange rate calculated from multiple data sources",
        "dependencies": {},
        "parameters": {}
    },

    "currency_yield": {
        "class": CurrencyYieldFactor,
        "name": "currency_yield",
        "group": "fundamental",
        "subgroup": "yield",
        "frequency": "1d",
        "data_type": "decimal",
        "description": "Short-term repo / risk-free yield for the currency (SOFR, ESTR, SONIA, etc.)",
        "dependencies": {},
        "parameters": {}
    },
}
