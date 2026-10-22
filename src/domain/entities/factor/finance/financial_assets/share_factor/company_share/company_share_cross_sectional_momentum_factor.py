"""
CompanyShareCrossSectionalMomentumFactor — LightGBM cross-sectional momentum classifier for company shares,
the counterpart of CompanyShareLGBMCSQuintileRankMomentumFactor with the features and the hyper-parameters
selected by an Optuna study (Tree-structured Parzen Estimator).

Candidates: the 24 momentum factors of LGBMMomentumFeatureDefinition (the same DependencySpecs as the
quintile-rank factor); each retraining keeps the subset Optuna selected.

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
        return momentum_feature_dependency_specs()

    def calculate(self, dependencies: dict) -> Optional[float]:
        """Return the classifier probability (0.0-1.0) or None."""
        if self._provider is None:
            return None
        entity = dependencies.get("entity")
        target_date = dependencies.get("target_date")
        if entity is None or target_date is None:
            return None
        return self._provider.predict(dependencies, entity, target_date)
