from datetime import timedelta
from typing import Dict, List

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_price_return_factor import CompanySharePriceReturnFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_avg_turnover_6m_factor import CompanyShareAvgTurnover6mFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_monthly_price_range_factor import CompanyShareMonthlyPriceRangeFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_vpt_52w_20d_lag_factor import CompanyShareVpt52w20dLagFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import CompanyShareValueFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_mid_price_factor import CompanyShareMidPriceFactor


COMPANY_SHARE_LIBRARY: Dict[str, Dict] = {

    "company_share_value": {
        "class": CompanyShareValueFactor,
        "name": "company_share_value",
        "group": "value",
        "subgroup": "asset",
        "frequency": "1d",
        "data_type": "decimal",
        "description": "Market value of a company share, derived from mid price",
        "dependencies": {
            "company_share_mid_price_factor": {
                "class": CompanyShareMidPriceFactor,
                "name": "mid_price",
                "group": "price",
                "subgroup": "mid_price_true",
                "data_type": "decimal",
                "description": "Mid price of the company share",
                "dependencies": {},
                "parameters": {}
            }
        },
        "parameters": {}
    },
    


    "implied_volatility": {
        "class": CompanyShareFactor, 
        "name": "close",
        "group": "implied_volatility",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level open volatility",
        "dependencies": [],
        "parameters": {}
    },
    "open": {
        "class": CompanyShareFactor,
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
        "class": CompanyShareFactor,
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
        "class": CompanyShareFactor,
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
        "class": CompanyShareFactor,
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
        "class": CompanyShareFactor,
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
        "class": CompanySharePriceReturnFactor,
        "name": "return_open",
        "group": "return",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level open price return",
        "dependencies": {
            "start_price": {
                "class": CompanyShareFactor,
                "name": "open",
                "group": "price",
                "subgroup": "minutes",
                "data_type": "numeric",
                "description": "Minute-level open price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=1, hours=0, minutes=0)}
            },
            "end_price": {
                "class": CompanyShareFactor,
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
        "class": CompanySharePriceReturnFactor,
        "name": "return_daily",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Daily price return",
        "dependencies": {
            "start_price": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily close price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=2, hours=0, minutes=0)}
            },
            "end_price": {
                "class": CompanyShareFactor,
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
    "return_daily_3": {
        "class": CompanySharePriceReturnFactor,
        "name": "return_daily",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Daily price return",
        "dependencies": {
            "start_price": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily close price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=5, hours=0, minutes=0)}
            },
            "end_price": {
                "class": CompanyShareFactor,
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
        "class": CompanySharePriceReturnFactor,
        "name": "return_weekly",
        "group": "return",
        "subgroup": "weekly",
        "frequency": "1w",
        "data_type": "numeric",
        "description": "Weekly price return",
        "dependencies": {
            "start_price": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "weekly",
                "data_type": "numeric",
                "description": "Weekly close price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=14, hours=0, minutes=0)}
            },
            "end_price": {
                "class": CompanyShareFactor,
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
        "class": CompanySharePriceReturnFactor,
        "name": "return_monthly",
        "group": "return",
        "subgroup": "monthly",
        "frequency": "1mth",
        "data_type": "numeric",
        "description": "Monthly price return",
        "dependencies": {
            "start_price": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "monthly",
                "data_type": "numeric",
                "description": "Monthly close price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=60, hours=0, minutes=0)}
            },
            "end_price": {
                "class": CompanyShareFactor,
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

    # ======================
    # 6-Month Average Share Turnover
    # ======================

    "avg_turnover_6m": {
        "class": CompanyShareAvgTurnover6mFactor,
        "name": "avg_turnover_6m",
        "group": "volume",
        "subgroup": "turnover",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "6-month (126-day) average daily share turnover (traded volume)",
        "dependencies": {
            "volume": {
                "class": CompanyShareFactor,
                "name": "volume",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily traded volume",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=1)}
            }
        },
        "parameters": {"period": 126}
    },

    # ======================
    # 1-Month Price High Minus 1-Month Price Low
    # ======================

    "monthly_price_range": {
        "class": CompanyShareMonthlyPriceRangeFactor,
        "name": "monthly_price_range",
        "group": "price",
        "subgroup": "range",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "1-month price high (lag=1d) minus 1-month price low (lag=21d)",
        "dependencies": {
            "high_price": {
                "class": CompanyShareFactor,
                "name": "high",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily high price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=1)}
            },
            "low_price": {
                "class": CompanyShareFactor,
                "name": "low",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily low price",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=21)}
            }
        },
        "parameters": {}
    },

    # ======================
    # 52-Week Volume Price Trend with 20-Day Lag
    # ======================

    "vpt_52w_20d_lag": {
        "class": CompanyShareVpt52w20dLagFactor,
        "name": "vpt_52w_20d_lag",
        "group": "volume",
        "subgroup": "trend",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "52-week Volume Price Trend observed with a 20-day lag",
        "dependencies": {
            "volume": {
                "class": CompanyShareFactor,
                "name": "volume",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily traded volume at 20-day lag",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=20)}
            },
            "close": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily close price at 20-day lag",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=20)}
            },
            "start_close": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily close price at 272-day lag (52 weeks + 20-day lag)",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=272)}
            }
        },
        "parameters": {}
    },
}
