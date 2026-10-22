"""
CSMFeatureDefinition — the candidate features of the cross-sectional classifier: the 24 momentum factors of
LGBMMomentumFeatureDefinition plus liquidity, volume-trend, price-range, return-extreme, relative-performance
(versus the SPY ETF) and delta-hedging-band factors of a reference call (48 in all).

Same contract as LGBMMomentumFeatureDefinition: FEATURE_MAP = (factor class name, feature name); ``extract`` builds
the vector from the resolved dependencies of CompanyShareCrossSectionalMomentumFactor (keyed by class name).
"""

from typing import List

from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_feature_definition import (
    LGBMMomentumFeatureDefinition,
)

EXTRA_FEATURE_MAP: List[tuple] = [
    ("CompanyShareAvgTurnover1mFactor",       "avg_turnover_1m"),
    ("CompanyShareAvgTurnover2mFactor",       "avg_turnover_2m"),
    ("CompanyShareAvgTurnover3mFactor",       "avg_turnover_3m"),
    ("CompanyShareAvgTurnover4mFactor",       "avg_turnover_4m"),
    ("CompanyShareAvgTurnover5mFactor",       "avg_turnover_5m"),
    ("CompanyShareAvgTurnover6mFactor",       "avg_turnover_6m"),
    ("CompanyShareTurnoverFactor",            "share_turnover"),
    ("CompanyShareVpt16w20dLagFactor",        "vpt_16w_20d_lag"),
    ("CompanyShareMonthlyPriceRangeFactor",   "monthly_price_range"),
    ("CompanyShareMaxDailyReturn6mFactor",    "max_daily_return_6m"),
    ("CompanyShareMinReturn120dFactor",       "min_return_120d"),
    ("CompanyShareRelativeReturnVsSpy1DFactor",  "rel_return_spy_1d"),
    ("CompanyShareRelativeReturnVsSpy5DFactor",  "rel_return_spy_5d"),
    ("CompanyShareRelativeReturnVsSpy20DFactor", "rel_return_spy_20d"),
    ("CompanyShareRelativeReturnVsSpy3MFactor",  "rel_return_spy_3m"),
    ("CompanyShareRelativeReturnVsSpy6MFactor",  "rel_return_spy_6m"),
    ("CompanyShareZakamoulineDeltaCeilingFactor",        "zakamouline_delta_ceiling"),
    ("CompanyShareZakamoulineDeltaFloorFactor",          "zakamouline_delta_floor"),
    ("CompanyShareWhalleyWilmottDeltaCeilingFactor",     "whalley_wilmott_delta_ceiling"),
    ("CompanyShareWhalleyWilmottDeltaFloorFactor",       "whalley_wilmott_delta_floor"),
    ("CompanyShareZakamoulineCeilingDistanceFactor",     "zakamouline_ceiling_distance"),
    ("CompanyShareZakamoulineFloorDistanceFactor",       "zakamouline_floor_distance"),
    ("CompanyShareWhalleyWilmottCeilingDistanceFactor",  "whalley_wilmott_ceiling_distance"),
    ("CompanyShareWhalleyWilmottFloorDistanceFactor",    "whalley_wilmott_floor_distance"),
]


class CSMFeatureDefinition(LGBMMomentumFeatureDefinition):
    FEATURE_MAP: List[tuple] = list(LGBMMomentumFeatureDefinition.FEATURE_MAP) + EXTRA_FEATURE_MAP
    FEATURE_NAMES: List[str] = [fn for _, fn in FEATURE_MAP]
    VERSION: int = 1
