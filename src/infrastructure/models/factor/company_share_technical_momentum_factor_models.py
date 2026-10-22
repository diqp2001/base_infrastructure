"""
ORM models for CompanyShare technical/momentum factors (single-table inheritance).
"""
from src.infrastructure.models.factor.factor import FactorModel


# ── Returns ──────────────────────────────────────────────────────────────────

class CompanyShareReturn1DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_return_1d_factor"}


class CompanyShareReturn5DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_return_5d_factor"}


class CompanyShareReturn10DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_return_10d_factor"}


class CompanyShareReturn20DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_return_20d_factor"}


class CompanyShareReturn1MFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_return_1m_factor"}


class CompanyShareReturn2MFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_return_2m_factor"}


class CompanyShareReturn3MFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_return_3m_factor"}


class CompanyShareReturn4MFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_return_4m_factor"}


class CompanyShareReturn5MFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_return_5m_factor"}


class CompanyShareReturnYTDFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_return_ytd_factor"}


# ── Moving Averages ───────────────────────────────────────────────────────────

class CompanySharePriceVsMA5FactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_price_vs_ma_5_factor"}


class CompanySharePriceVsMA10FactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_price_vs_ma_10_factor"}


class CompanySharePriceVsMA20FactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_price_vs_ma_20_factor"}


class CompanySharePriceVsMA50FactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_price_vs_ma_50_factor"}


class CompanySharePriceVsMA100FactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_price_vs_ma_100_factor"}


class CompanyShareMA5VsMA10FactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_ma_5_vs_ma_10_factor"}


class CompanyShareMA10VsMA20FactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_ma_10_vs_ma_20_factor"}


class CompanyShareMA20VsMA50FactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_ma_20_vs_ma_50_factor"}


class CompanyShareMA50VsMA100FactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_ma_50_vs_ma_100_factor"}


# ── Trend / Momentum Slopes ───────────────────────────────────────────────────

class CompanyShareTrendSlope5DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_trend_slope_5d_factor"}


class CompanyShareTrendSlope10DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_trend_slope_10d_factor"}


class CompanyShareTrendSlope20DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_trend_slope_20d_factor"}


class CompanyShareTrendSlope50DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_trend_slope_50d_factor"}


class CompanyShareTrendSlope100DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_trend_slope_100d_factor"}


class CompanyShareMomentumSlope10DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_momentum_slope_10d_factor"}


class CompanyShareMomentumSlope20DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_momentum_slope_20d_factor"}


class CompanyShareMomentumSlope50DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_momentum_slope_50d_factor"}


# ── Momentum Acceleration / Return Change ─────────────────────────────────────

class CompanyShareMomentumAcceleration5D10DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_momentum_accel_5d_10d_factor"}


class CompanyShareMomentumAcceleration10D20DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_momentum_accel_10d_20d_factor"}


class CompanyShareMomentumAcceleration20D50DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_momentum_accel_20d_50d_factor"}


class CompanyShareReturnChange5DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_return_change_5d_factor"}


class CompanyShareReturnChange10DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_return_change_10d_factor"}


class CompanyShareReturnChange20DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_return_change_20d_factor"}


# ── Risk ──────────────────────────────────────────────────────────────────────

class CompanyShareSharpe10DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_sharpe_10d_factor"}


class CompanyShareSharpe20DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_sharpe_20d_factor"}


class CompanyShareSharpe50DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_sharpe_50d_factor"}


class CompanyShareSharpe100DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_sharpe_100d_factor"}


class CompanyShareSortino20DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_sortino_20d_factor"}


class CompanyShareSortino50DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_sortino_50d_factor"}


class CompanyShareSortino100DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_sortino_100d_factor"}


# ── Drawdown / Distance ───────────────────────────────────────────────────────

class CompanyShareDistanceFrom5MHighFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_distance_from_5m_high_factor"}


class CompanyShareDistanceFrom5MLowFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_distance_from_5m_low_factor"}


class CompanyShareDrawdownFrom5MHighFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_drawdown_from_5m_high_factor"}


class CompanyShareDaysSince5MHighFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_days_since_5m_high_factor"}


class CompanyShareDaysSince5MLowFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_days_since_5m_low_factor"}


# ── Composite Momentum ────────────────────────────────────────────────────────

class CompanyShareShortTermMomentumFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_short_term_momentum_factor"}


class CompanyShareMediumTermMomentumFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_medium_term_momentum_factor"}


class CompanyShareShortVsMediumMomentumFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_short_vs_medium_momentum_factor"}


class CompanyShareMomentumZScore20DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_momentum_zscore_20d_factor"}


class CompanyShareMomentumZScore50DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_momentum_zscore_50d_factor"}


class CompanyShareMomentumZScore100DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_momentum_zscore_100d_factor"}


# ── ML / LightGBM ─────────────────────────────────────────────────────────────

class CompanyShareLGBMCSQuintileRankMomentumFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_lgbm_cs_quintile_rank_momentum_factor"}


# ── ML / Spatio-Temporal Momentum ─────────────────────────────────────────────

class CompanyShareSpatioTemporalMomentumFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_spatio_temporal_momentum_factor"}


class CompanyShareSpatioTemporalFeatureFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_spatio_temporal_feature_factor"}


class CompanyShareCrossSectionalMomentumFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_cross_sectional_momentum_factor"}


# ── Liquidity, volume-trend and return-extreme factors ────────────────────────


class CompanyShareAvgTurnover1mFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_avg_turnover_1m_factor"}


class CompanyShareAvgTurnover2mFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_avg_turnover_2m_factor"}


class CompanyShareAvgTurnover3mFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_avg_turnover_3m_factor"}


class CompanyShareAvgTurnover4mFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_avg_turnover_4m_factor"}


class CompanyShareAvgTurnover5mFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_avg_turnover_5m_factor"}


class CompanyShareTurnoverFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_turnover_factor"}


class CompanyShareVpt16w20dLagFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_vpt_16w_20d_lag_factor"}


class CompanyShareMaxDailyReturn6mFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_max_daily_return_6m_factor"}


class CompanyShareMinReturn120dFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_min_return_120d_factor"}


# ── Relative performance versus SPY factors ────────────────────────


class CompanyShareRelativeReturnVsSpy1DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_relative_return_vs_spy_1d_factor"}


class CompanyShareRelativeReturnVsSpy5DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_relative_return_vs_spy_5d_factor"}


class CompanyShareRelativeReturnVsSpy20DFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_relative_return_vs_spy_20d_factor"}


class CompanyShareRelativeReturnVsSpy3MFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_relative_return_vs_spy_3m_factor"}


class CompanyShareRelativeReturnVsSpy6MFactorModel(FactorModel):
    __mapper_args__ = {"polymorphic_identity": "company_share_relative_return_vs_spy_6m_factor"}
