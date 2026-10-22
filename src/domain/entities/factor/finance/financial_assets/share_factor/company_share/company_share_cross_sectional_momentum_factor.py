"""
CompanyShareCrossSectionalMomentumFactor — LightGBM cross-sectional momentum classifier for company shares,
the counterpart of CompanyShareLGBMCSQuintileRankMomentumFactor with the features and the hyper-parameters
selected by an Optuna study (Tree-structured Parzen Estimator).

Candidates: the 24 momentum factors of LGBMMomentumFeatureDefinition (the same DependencySpecs as the
quintile-rank factor) plus 11 liquidity / volume-trend / price-range / return-extreme factors (share turnover
averaged over 1-6 months, daily share turnover, 16-week VPT with a 20-day lag, 1-month high minus low, largest
daily return over 6 months, smallest daily return over 120 days) and 5 relative-performance factors versus the SPY
ETF (1, 5, 20 sessions, 3 and 6 months); each retraining keeps the subset Optuna selected.

Output: probability (0-1) that the share's next-session return beats the cross-sectional median.

``calculate`` delegates to an injected provider (application layer): the trading cycle's stored decision for the
date when there is one, otherwise the model valid at the date applied to the resolved momentum features. The
domain entity knows nothing about LightGBM or Optuna.
"""

from typing import Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
    CompanyShareFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_lgbm_cs_quintile_rank_momentum_factor import (
    momentum_feature_dependency_specs,
)


def cross_sectional_extra_factor_classes() -> list:
    """The non-momentum candidates, in CSMFeatureDefinition.EXTRA_FEATURE_MAP order."""
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_avg_turnover_6m_factor import (
        CompanyShareAvgTurnover6mFactor,
    )
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_liquidity_factors import (
        CompanyShareAvgTurnover1mFactor, CompanyShareAvgTurnover2mFactor, CompanyShareAvgTurnover3mFactor,
        CompanyShareAvgTurnover4mFactor, CompanyShareAvgTurnover5mFactor, CompanyShareMaxDailyReturn6mFactor,
        CompanyShareMinReturn120dFactor, CompanyShareTurnoverFactor, CompanyShareVpt16w20dLagFactor,
    )
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_monthly_price_range_factor import (
        CompanyShareMonthlyPriceRangeFactor,
    )
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_relative_performance_factors import (
        RELATIVE_PERFORMANCE_FACTOR_CLASSES,
    )
    return [CompanyShareAvgTurnover1mFactor, CompanyShareAvgTurnover2mFactor, CompanyShareAvgTurnover3mFactor,
            CompanyShareAvgTurnover4mFactor, CompanyShareAvgTurnover5mFactor, CompanyShareAvgTurnover6mFactor,
            CompanyShareTurnoverFactor, CompanyShareVpt16w20dLagFactor, CompanyShareMonthlyPriceRangeFactor,
            CompanyShareMaxDailyReturn6mFactor, CompanyShareMinReturn120dFactor,
            *RELATIVE_PERFORMANCE_FACTOR_CLASSES]


def cross_sectional_feature_dependency_specs() -> list:
    """The 24 momentum specs + one spec per extra factor (calculated values, its own group, parent's frequency)."""
    from src.domain.entities.factor.dependency_spec import DependencySpec
    extra = [DependencySpec(factor_type=cls, group=cls().group, frequency=DependencySpec.SELF, source_in=["calculated"])
             for cls in cross_sectional_extra_factor_classes()]
    return momentum_feature_dependency_specs() + extra


class CompanyShareCrossSectionalMomentumFactor(CompanyShareFactor):
    """
    LightGBM cross-sectional momentum classifier (features + hyper-parameters by Optuna TPE).

    Output: float 0.0-1.0 (probability of beating the cross-sectional median next session).
    """

    def __init__(
        self,
        name: str = "cross_sectional_momentum_signal",
        group: str = "momentum",
        subgroup: Optional[str] = "daily",
        data_type: Optional[str] = "numeric",
        source: Optional[str] = "calculated",
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        frequency: Optional[str] = "1d",
        provider=None,
        **kwargs,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
            frequency=frequency,
            **kwargs,
        )
        self._provider = provider

    @property
    def calculate_dependencies(self) -> list:
        return cross_sectional_feature_dependency_specs()

    def calculate(self, dependencies: dict) -> Optional[float]:
        """Return the classifier probability (0.0-1.0) or None."""
        if self._provider is None:
            return None
        entity = dependencies.get("entity")
        target_date = dependencies.get("target_date")
        if entity is None or target_date is None:
            return None
        return self._provider.predict(dependencies, entity, target_date)
