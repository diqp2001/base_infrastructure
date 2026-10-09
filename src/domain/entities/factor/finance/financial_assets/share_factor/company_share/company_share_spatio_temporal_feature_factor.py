"""
CompanyShareSpatioTemporalFeatureFactor — one input feature of the
Spatio-Temporal Momentum model (e.g. ``stm_norm_monthly_return``,
``stm_macd_8_24``).

A single class represents every feature; the feature is identified by the
factor ``name``.  Values are produced in batch from the daily close history
by the STM feature service (exponentially weighted statistics cannot be
reproduced point-by-point without the full history), then stored in
``factor_values`` like any other factor — the same pattern as
ConstituentScoreFactor ("written directly by ML pipeline services").
"""

from typing import Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
    CompanyShareFactor,
)


class CompanyShareSpatioTemporalFeatureFactor(CompanyShareFactor):

    def __init__(
        self,
        name: str = "stm_feature",
        group: str = "momentum",
        subgroup: Optional[str] = "daily",
        data_type: Optional[str] = "numeric",
        source: Optional[str] = "calculated",
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        frequency: Optional[str] = "1d",
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
