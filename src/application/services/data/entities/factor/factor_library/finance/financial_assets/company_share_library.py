from datetime import timedelta
from typing import Dict, List

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_price_return_factor import CompanySharePriceReturnFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_avg_turnover_6m_factor import CompanyShareAvgTurnover6mFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_monthly_price_range_factor import CompanyShareMonthlyPriceRangeFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_vpt_52w_20d_lag_factor import CompanyShareVpt52w20dLagFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import CompanyShareValueFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_mid_price_factor import CompanyShareMidPriceFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_atm_implied_vol_factor import CompanyShareATMImpliedVolFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_return_factors import (
    CompanyShareReturn1DFactor, CompanyShareReturn5DFactor, CompanyShareReturn10DFactor,
    CompanyShareReturn20DFactor, CompanyShareReturn1MFactor, CompanyShareReturn2MFactor,
    CompanyShareReturn3MFactor, CompanyShareReturn4MFactor, CompanyShareReturn5MFactor,
    CompanyShareReturnYTDFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_ma_factors import (
    CompanySharePriceVsMA5Factor, CompanySharePriceVsMA10Factor, CompanySharePriceVsMA20Factor,
    CompanySharePriceVsMA50Factor, CompanySharePriceVsMA100Factor,
    CompanyShareMA5VsMA10Factor, CompanyShareMA10VsMA20Factor,
    CompanyShareMA20VsMA50Factor, CompanyShareMA50VsMA100Factor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_trend_factors import (
    CompanyShareTrendSlope5DFactor, CompanyShareTrendSlope10DFactor, CompanyShareTrendSlope20DFactor,
    CompanyShareTrendSlope50DFactor, CompanyShareTrendSlope100DFactor,
    CompanyShareMomentumSlope10DFactor, CompanyShareMomentumSlope20DFactor, CompanyShareMomentumSlope50DFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_momentum_change_factors import (
    CompanyShareMomentumAcceleration5D10DFactor, CompanyShareMomentumAcceleration10D20DFactor,
    CompanyShareMomentumAcceleration20D50DFactor,
    CompanyShareReturnChange5DFactor, CompanyShareReturnChange10DFactor, CompanyShareReturnChange20DFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_risk_factors import (
    CompanyShareSharpe10DFactor, CompanyShareSharpe20DFactor, CompanyShareSharpe50DFactor,
    CompanyShareSharpe100DFactor, CompanyShareSortino20DFactor, CompanyShareSortino50DFactor,
    CompanyShareSortino100DFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_drawdown_factors import (
    CompanyShareDistanceFrom5MHighFactor, CompanyShareDistanceFrom5MLowFactor,
    CompanyShareDrawdownFrom5MHighFactor, CompanyShareDaysSince5MHighFactor, CompanyShareDaysSince5MLowFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_composite_momentum_factors import (
    CompanyShareShortTermMomentumFactor, CompanyShareMediumTermMomentumFactor,
    CompanyShareShortVsMediumMomentumFactor, CompanyShareMomentumZScore20DFactor,
    CompanyShareMomentumZScore50DFactor, CompanyShareMomentumZScore100DFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_lgbm_cs_quintile_rank_momentum_factor import (
    CompanyShareLGBMCSQuintileRankMomentumFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_spatio_temporal_momentum_factor import (
    CompanyShareSpatioTemporalMomentumFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_spatio_temporal_feature_factor import (
    CompanyShareSpatioTemporalFeatureFactor,
)


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
        },
        "parameters": {}
    },
    


    "atm_implied_vol": {
        "class": CompanyShareATMImpliedVolFactor,
        "name": "atm_implied_vol",
        "group": "volatility",
        "subgroup": "implied",
        "frequency": "1d",
        "data_type": "decimal",
        "description": "At-the-money implied volatility derived from IBKR option chain",
        "dependencies": {},
        "parameters": {}
    },

    "implied_volatility": {
        "class": CompanyShareFactor,
        "name": "implied_volatility",
        "group": "volatility",
        "subgroup": "implied",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Minute-level implied volatility",
        "source": "ibkr",
        "dependencies": [],
        "parameters": {}
    },
    "open": {
        "class": CompanyShareFactor,
        "name": "open",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1d",
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
        "frequency": "1d",
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
        "frequency": "1d",
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
        "frequency": "1d",
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
        "frequency": "1d",
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
        "frequency": "5m",
        "data_type": "numeric",
        "description": "Minute-level open price return",
        "dependencies": {
            "start_price": {
                "class": CompanyShareFactor,
                "name": "open",
                "group": "price",
                "subgroup": "minutes",
                "frequency": "5m",
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
                "frequency": "5m",
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
                "frequency": "1d",
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
                "frequency": "1d",
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
                "frequency": "1d",
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
                "frequency": "1d",
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
                "frequency": "1w",
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
                "frequency": "1w",
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
                "frequency": "1mth",
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
                "frequency": "1mth",
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
                "frequency": "1d",
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
                "frequency": "1d",
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
                "frequency": "1d",
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
                "frequency": "1d",
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
                "frequency": "1d",
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
                "frequency": "1d",
                "data_type": "numeric",
                "description": "Daily close price at 272-day lag (52 weeks + 20-day lag)",
                "dependencies": {},
                "parameters": {"lag": timedelta(days=272)}
            }
        },
        "parameters": {}
    },

    # ==========================
    # Technical / Momentum — Returns
    # ==========================

    "return_1d": {
        "class": CompanyShareReturn1DFactor,
        "name": "return_1d",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "1-day price return",
        "dependencies": {},
        "parameters": {}
    },
    "return_5d": {
        "class": CompanyShareReturn5DFactor,
        "name": "return_5d",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "5-day price return",
        "dependencies": {},
        "parameters": {}
    },
    "return_10d": {
        "class": CompanyShareReturn10DFactor,
        "name": "return_10d",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "10-day price return",
        "dependencies": {},
        "parameters": {}
    },
    "return_20d": {
        "class": CompanyShareReturn20DFactor,
        "name": "return_20d",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "20-day price return",
        "dependencies": {},
        "parameters": {}
    },
    "return_1m": {
        "class": CompanyShareReturn1MFactor,
        "name": "return_1m",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "1-month (~21-day) price return",
        "dependencies": {},
        "parameters": {}
    },
    "return_2m": {
        "class": CompanyShareReturn2MFactor,
        "name": "return_2m",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "2-month (~42-day) price return",
        "dependencies": {},
        "parameters": {}
    },
    "return_3m": {
        "class": CompanyShareReturn3MFactor,
        "name": "return_3m",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "3-month (~63-day) price return",
        "dependencies": {},
        "parameters": {}
    },
    "return_4m": {
        "class": CompanyShareReturn4MFactor,
        "name": "return_4m",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "4-month (~84-day) price return",
        "dependencies": {},
        "parameters": {}
    },
    "return_5m": {
        "class": CompanyShareReturn5MFactor,
        "name": "return_5m",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "5-month (~105-day) price return",
        "dependencies": {},
        "parameters": {}
    },
    "return_ytd": {
        "class": CompanyShareReturnYTDFactor,
        "name": "return_ytd",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Year-to-date price return",
        "dependencies": {},
        "parameters": {}
    },

    # ==========================
    # Technical / Momentum — Moving Averages
    # ==========================

    "price_vs_ma_5": {
        "class": CompanySharePriceVsMA5Factor,
        "name": "price_vs_ma_5",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Price relative to 5-day moving average",
        "dependencies": {},
        "parameters": {}
    },
    "price_vs_ma_10": {
        "class": CompanySharePriceVsMA10Factor,
        "name": "price_vs_ma_10",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Price relative to 10-day moving average",
        "dependencies": {},
        "parameters": {}
    },
    "price_vs_ma_20": {
        "class": CompanySharePriceVsMA20Factor,
        "name": "price_vs_ma_20",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Price relative to 20-day moving average",
        "dependencies": {},
        "parameters": {}
    },
    "price_vs_ma_50": {
        "class": CompanySharePriceVsMA50Factor,
        "name": "price_vs_ma_50",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Price relative to 50-day moving average",
        "dependencies": {},
        "parameters": {}
    },
    "price_vs_ma_100": {
        "class": CompanySharePriceVsMA100Factor,
        "name": "price_vs_ma_100",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Price relative to 100-day moving average",
        "dependencies": {},
        "parameters": {}
    },
    "ma_5_vs_ma_10": {
        "class": CompanyShareMA5VsMA10Factor,
        "name": "ma_5_vs_ma_10",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "5-day MA relative to 10-day MA",
        "dependencies": {},
        "parameters": {}
    },
    "ma_10_vs_ma_20": {
        "class": CompanyShareMA10VsMA20Factor,
        "name": "ma_10_vs_ma_20",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "10-day MA relative to 20-day MA",
        "dependencies": {},
        "parameters": {}
    },
    "ma_20_vs_ma_50": {
        "class": CompanyShareMA20VsMA50Factor,
        "name": "ma_20_vs_ma_50",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "20-day MA relative to 50-day MA",
        "dependencies": {},
        "parameters": {}
    },
    "ma_50_vs_ma_100": {
        "class": CompanyShareMA50VsMA100Factor,
        "name": "ma_50_vs_ma_100",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "50-day MA relative to 100-day MA",
        "dependencies": {},
        "parameters": {}
    },

    # ==========================
    # Technical / Momentum — Trend Slopes
    # ==========================

    "trend_slope_5d": {
        "class": CompanyShareTrendSlope5DFactor,
        "name": "trend_slope_5d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Linear trend slope over 5 days",
        "dependencies": {},
        "parameters": {}
    },
    "trend_slope_10d": {
        "class": CompanyShareTrendSlope10DFactor,
        "name": "trend_slope_10d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Linear trend slope over 10 days",
        "dependencies": {},
        "parameters": {}
    },
    "trend_slope_20d": {
        "class": CompanyShareTrendSlope20DFactor,
        "name": "trend_slope_20d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Linear trend slope over 20 days",
        "dependencies": {},
        "parameters": {}
    },
    "trend_slope_50d": {
        "class": CompanyShareTrendSlope50DFactor,
        "name": "trend_slope_50d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Linear trend slope over 50 days",
        "dependencies": {},
        "parameters": {}
    },
    "trend_slope_100d": {
        "class": CompanyShareTrendSlope100DFactor,
        "name": "trend_slope_100d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Linear trend slope over 100 days",
        "dependencies": {},
        "parameters": {}
    },
    "momentum_slope_10d": {
        "class": CompanyShareMomentumSlope10DFactor,
        "name": "momentum_slope_10d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Momentum (return) slope over 10 days",
        "dependencies": {},
        "parameters": {}
    },
    "momentum_slope_20d": {
        "class": CompanyShareMomentumSlope20DFactor,
        "name": "momentum_slope_20d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Momentum (return) slope over 20 days",
        "dependencies": {},
        "parameters": {}
    },
    "momentum_slope_50d": {
        "class": CompanyShareMomentumSlope50DFactor,
        "name": "momentum_slope_50d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Momentum (return) slope over 50 days",
        "dependencies": {},
        "parameters": {}
    },

    # ==========================
    # Technical / Momentum — Acceleration & Return Change
    # ==========================

    "momentum_accel_5d_10d": {
        "class": CompanyShareMomentumAcceleration5D10DFactor,
        "name": "momentum_accel_5d_10d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Momentum acceleration: 5-day slope minus 10-day slope",
        "dependencies": {},
        "parameters": {}
    },
    "momentum_accel_10d_20d": {
        "class": CompanyShareMomentumAcceleration10D20DFactor,
        "name": "momentum_accel_10d_20d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Momentum acceleration: 10-day slope minus 20-day slope",
        "dependencies": {},
        "parameters": {}
    },
    "momentum_accel_20d_50d": {
        "class": CompanyShareMomentumAcceleration20D50DFactor,
        "name": "momentum_accel_20d_50d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Momentum acceleration: 20-day slope minus 50-day slope",
        "dependencies": {},
        "parameters": {}
    },
    "return_change_5d": {
        "class": CompanyShareReturnChange5DFactor,
        "name": "return_change_5d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Change in 5-day return (current minus lagged)",
        "dependencies": {},
        "parameters": {}
    },
    "return_change_10d": {
        "class": CompanyShareReturnChange10DFactor,
        "name": "return_change_10d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Change in 10-day return (current minus lagged)",
        "dependencies": {},
        "parameters": {}
    },
    "return_change_20d": {
        "class": CompanyShareReturnChange20DFactor,
        "name": "return_change_20d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Change in 20-day return (current minus lagged)",
        "dependencies": {},
        "parameters": {}
    },

    # ==========================
    # Technical / Momentum — Risk (Sharpe / Sortino)
    # ==========================

    "sharpe_10d": {
        "class": CompanyShareSharpe10DFactor,
        "name": "sharpe_10d",
        "group": "risk",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "10-day Sharpe ratio",
        "dependencies": {},
        "parameters": {}
    },
    "sharpe_20d": {
        "class": CompanyShareSharpe20DFactor,
        "name": "sharpe_20d",
        "group": "risk",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "20-day Sharpe ratio",
        "dependencies": {},
        "parameters": {}
    },
    "sharpe_50d": {
        "class": CompanyShareSharpe50DFactor,
        "name": "sharpe_50d",
        "group": "risk",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "50-day Sharpe ratio",
        "dependencies": {},
        "parameters": {}
    },
    "sharpe_100d": {
        "class": CompanyShareSharpe100DFactor,
        "name": "sharpe_100d",
        "group": "risk",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "100-day Sharpe ratio",
        "dependencies": {},
        "parameters": {}
    },
    "sortino_20d": {
        "class": CompanyShareSortino20DFactor,
        "name": "sortino_20d",
        "group": "risk",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "20-day Sortino ratio",
        "dependencies": {},
        "parameters": {}
    },
    "sortino_50d": {
        "class": CompanyShareSortino50DFactor,
        "name": "sortino_50d",
        "group": "risk",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "50-day Sortino ratio",
        "dependencies": {},
        "parameters": {}
    },
    "sortino_100d": {
        "class": CompanyShareSortino100DFactor,
        "name": "sortino_100d",
        "group": "risk",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "100-day Sortino ratio",
        "dependencies": {},
        "parameters": {}
    },

    # ==========================
    # Technical / Momentum — Drawdown / Distance
    # ==========================

    "distance_from_5m_high": {
        "class": CompanyShareDistanceFrom5MHighFactor,
        "name": "distance_from_5m_high",
        "group": "risk",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Distance from 5-month rolling high (price / max - 1)",
        "dependencies": {},
        "parameters": {}
    },
    "distance_from_5m_low": {
        "class": CompanyShareDistanceFrom5MLowFactor,
        "name": "distance_from_5m_low",
        "group": "risk",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Distance from 5-month rolling low (price / min - 1)",
        "dependencies": {},
        "parameters": {}
    },
    "drawdown_from_5m_high": {
        "class": CompanyShareDrawdownFrom5MHighFactor,
        "name": "drawdown_from_5m_high",
        "group": "risk",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Drawdown from 5-month rolling high",
        "dependencies": {},
        "parameters": {}
    },
    "days_since_5m_high": {
        "class": CompanyShareDaysSince5MHighFactor,
        "name": "days_since_5m_high",
        "group": "risk",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Number of days since the 5-month rolling high",
        "dependencies": {},
        "parameters": {}
    },
    "days_since_5m_low": {
        "class": CompanyShareDaysSince5MLowFactor,
        "name": "days_since_5m_low",
        "group": "risk",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Number of days since the 5-month rolling low",
        "dependencies": {},
        "parameters": {}
    },

    # ==========================
    # Technical / Momentum — Composite Momentum
    # ==========================

    "short_term_momentum": {
        "class": CompanyShareShortTermMomentumFactor,
        "name": "short_term_momentum",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Composite short-term momentum signal",
        "dependencies": {},
        "parameters": {}
    },
    "medium_term_momentum": {
        "class": CompanyShareMediumTermMomentumFactor,
        "name": "medium_term_momentum",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Composite medium-term momentum signal",
        "dependencies": {},
        "parameters": {}
    },
    "short_vs_medium_momentum": {
        "class": CompanyShareShortVsMediumMomentumFactor,
        "name": "short_vs_medium_momentum",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Short-term momentum relative to medium-term momentum",
        "dependencies": {},
        "parameters": {}
    },
    "momentum_zscore_20d": {
        "class": CompanyShareMomentumZScore20DFactor,
        "name": "momentum_zscore_20d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "20-day momentum Z-score",
        "dependencies": {},
        "parameters": {}
    },
    "momentum_zscore_50d": {
        "class": CompanyShareMomentumZScore50DFactor,
        "name": "momentum_zscore_50d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "50-day momentum Z-score",
        "dependencies": {},
        "parameters": {}
    },
    "momentum_zscore_100d": {
        "class": CompanyShareMomentumZScore100DFactor,
        "name": "momentum_zscore_100d",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "100-day momentum Z-score",
        "dependencies": {},
        "parameters": {}
    },
    "lgbm_cs_quintile_rank_momentum": {
        "class": CompanyShareLGBMCSQuintileRankMomentumFactor,
        "name": "lgbm_cs_quintile_rank_momentum",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "LightGBM cross-sectional quintile rank momentum factor (1=weakest, 5=strongest)",
        "dependencies": {},
        "parameters": {}
    },    # ── Spatio-Temporal Momentum (Tan, Roberts, Zohren 2023) ─────────────────
    # Signal: joint-universe model output; values produced by the STM provider.
    "spatio_temporal_momentum_signal": {
        "class": CompanyShareSpatioTemporalMomentumFactor,
        "name": "spatio_temporal_momentum_signal",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Spatio-Temporal Momentum model signal (one per universe constituent)",
        "dependencies": {},
        "parameters": {}
    },
    "stm_norm_daily_return": {
        "class": CompanyShareSpatioTemporalFeatureFactor,
        "name": "stm_norm_daily_return",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "STM input feature: 1-day return / daily EWM vol",
        "dependencies": {},
        "parameters": {}
    },
    "stm_norm_monthly_return": {
        "class": CompanyShareSpatioTemporalFeatureFactor,
        "name": "stm_norm_monthly_return",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "STM input feature: 21-day return / daily vol / sqrt(21)",
        "dependencies": {},
        "parameters": {}
    },
    "stm_norm_quarterly_return": {
        "class": CompanyShareSpatioTemporalFeatureFactor,
        "name": "stm_norm_quarterly_return",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "STM input feature: 63-day return / daily vol / sqrt(63)",
        "dependencies": {},
        "parameters": {}
    },
    "stm_norm_biannual_return": {
        "class": CompanyShareSpatioTemporalFeatureFactor,
        "name": "stm_norm_biannual_return",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "STM input feature: 126-day return / daily vol / sqrt(126)",
        "dependencies": {},
        "parameters": {}
    },
    "stm_norm_annual_return": {
        "class": CompanyShareSpatioTemporalFeatureFactor,
        "name": "stm_norm_annual_return",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "STM input feature: 252-day return / daily vol / sqrt(252)",
        "dependencies": {},
        "parameters": {}
    },
    "stm_macd_8_24": {
        "class": CompanyShareSpatioTemporalFeatureFactor,
        "name": "stm_macd_8_24",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "STM input feature: MACD(8,24) normalised by 63d price std and 252d signal std",
        "dependencies": {},
        "parameters": {}
    },
    "stm_macd_16_48": {
        "class": CompanyShareSpatioTemporalFeatureFactor,
        "name": "stm_macd_16_48",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "STM input feature: MACD(16,48) normalised by 63d price std and 252d signal std",
        "dependencies": {},
        "parameters": {}
    },
    "stm_macd_32_96": {
        "class": CompanyShareSpatioTemporalFeatureFactor,
        "name": "stm_macd_32_96",
        "group": "momentum",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "STM input feature: MACD(32,96) normalised by 63d price std and 252d signal std",
        "dependencies": {},
        "parameters": {}
    },
}
