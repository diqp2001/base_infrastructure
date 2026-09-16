import hashlib
import json
from typing import List, Optional


class LGBMMomentumFeatureDefinition:
    """
    24-dimensional feature vector built from momentum factor values.

    Each feature maps to one CompanyShare momentum factor class.
    The key in the dependencies dict is the factor class name; the value
    is a scalar or list delivered by DependencySpec resolution.
    """

    # (class_name, feature_name) pairs — order determines column index in X
    FEATURE_MAP: List[tuple] = [
        ("CompanyShareReturn1DFactor",         "return_1d"),
        ("CompanyShareReturn5DFactor",         "return_5d"),
        ("CompanyShareReturn20DFactor",        "return_20d"),
        ("CompanyShareReturn1MFactor",         "return_1m"),
        ("CompanyShareReturn3MFactor",         "return_3m"),
        ("CompanyShareReturn5MFactor",         "return_5m"),
        ("CompanyShareReturnYTDFactor",        "return_ytd"),
        ("CompanySharePriceVsMA20Factor",      "price_vs_ma_20"),
        ("CompanySharePriceVsMA50Factor",      "price_vs_ma_50"),
        ("CompanySharePriceVsMA100Factor",     "price_vs_ma_100"),
        ("CompanyShareMA5VsMA10Factor",        "ma_5_vs_ma_10"),
        ("CompanyShareMA20VsMA50Factor",       "ma_20_vs_ma_50"),
        ("CompanyShareTrendSlope20DFactor",    "trend_slope_20d"),
        ("CompanyShareTrendSlope50DFactor",    "trend_slope_50d"),
        ("CompanyShareMomentumSlope20DFactor", "momentum_slope_20d"),
        ("CompanyShareSharpe20DFactor",        "sharpe_20d"),
        ("CompanyShareSharpe50DFactor",        "sharpe_50d"),
        ("CompanyShareSortino20DFactor",       "sortino_20d"),
        ("CompanyShareDistanceFrom5MHighFactor",  "distance_from_5m_high"),
        ("CompanyShareDrawdownFrom5MHighFactor",  "drawdown_from_5m_high"),
        ("CompanyShareDaysSince5MHighFactor",     "days_since_5m_high"),
        ("CompanyShareShortTermMomentumFactor",   "short_term_momentum"),
        ("CompanyShareMediumTermMomentumFactor",  "medium_term_momentum"),
        ("CompanyShareMomentumZScore20DFactor",   "momentum_zscore_20d"),
    ]

    FEATURE_NAMES: List[str] = [fn for _, fn in FEATURE_MAP]
    VERSION: int = 1

    def hash(self) -> str:
        canonical = {"features": self.FEATURE_NAMES, "version": self.VERSION}
        return hashlib.sha256(
            json.dumps(canonical, sort_keys=True).encode()
        ).hexdigest()

    def extract(self, dependencies: dict, entity, target_date) -> Optional[List[float]]:
        """
        Build feature vector from the resolved dependency dict.

        Returns None if any required feature is missing or invalid.
        """
        features = []
        for cls_name, _ in self.FEATURE_MAP:
            raw = dependencies.get(cls_name)
            if raw is None:
                return None
            vals = raw if isinstance(raw, list) else [raw]
            vals = [v for v in vals if v is not None]
            if not vals:
                return None
            try:
                numeric = [float(v) for v in vals]
            except (ValueError, TypeError):
                return None
            features.append(sum(numeric) / len(numeric))
        return features
