"""
CompanyShareLGBMCSQuintileRankMomentumFactor — LightGBM cross-sectional
quintile rank momentum factor for company shares.

Classifies each stock into quintile 1–5 based on predicted 1-week forward
return, trained on the 24 momentum features defined in LGBMMomentumFeatureDefinition.
"""

from typing import Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
    CompanyShareFactor,
)


class CompanyShareLGBMCSQuintileRankMomentumFactor(CompanyShareFactor):
    """
    LightGBM cross-sectional quintile rank momentum factor.

    Output: float 1.0–5.0 (quintile rank, 1 = weakest, 5 = strongest momentum).
    """

    def __init__(
        self,
        name: str = "lgbm_cs_quintile_rank_momentum",
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
        from src.domain.entities.factor.dependency_spec import DependencySpec
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_return_factors import (
            CompanyShareReturn1DFactor,
            CompanyShareReturn5DFactor,
            CompanyShareReturn20DFactor,
            CompanyShareReturn1MFactor,
            CompanyShareReturn3MFactor,
            CompanyShareReturn5MFactor,
            CompanyShareReturnYTDFactor,
        )
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_ma_factors import (
            CompanySharePriceVsMA20Factor,
            CompanySharePriceVsMA50Factor,
            CompanySharePriceVsMA100Factor,
            CompanyShareMA5VsMA10Factor,
            CompanyShareMA20VsMA50Factor,
        )
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_trend_factors import (
            CompanyShareTrendSlope20DFactor,
            CompanyShareTrendSlope50DFactor,
            CompanyShareMomentumSlope20DFactor,
        )
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_risk_factors import (
            CompanyShareSharpe20DFactor,
            CompanyShareSharpe50DFactor,
            CompanyShareSortino20DFactor,
        )
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_drawdown_factors import (
            CompanyShareDistanceFrom5MHighFactor,
            CompanyShareDrawdownFrom5MHighFactor,
            CompanyShareDaysSince5MHighFactor,
        )
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_composite_momentum_factors import (
            CompanyShareShortTermMomentumFactor,
            CompanyShareMediumTermMomentumFactor,
            CompanyShareMomentumZScore20DFactor,
        )

        # Each factor's group must match what _create_or_get stores in the DB.
        # Return factors → "return"; risk factors → "risk"; everything else → "momentum".
        return_factors = [
            CompanyShareReturn1DFactor,
            CompanyShareReturn5DFactor,
            CompanyShareReturn20DFactor,
            CompanyShareReturn1MFactor,
            CompanyShareReturn3MFactor,
            CompanyShareReturn5MFactor,
            CompanyShareReturnYTDFactor,
        ]
        risk_factors = [
            CompanyShareSharpe20DFactor,
            CompanyShareSharpe50DFactor,
            CompanyShareSortino20DFactor,
        ]
        momentum_factors = [
            CompanySharePriceVsMA20Factor,
            CompanySharePriceVsMA50Factor,
            CompanySharePriceVsMA100Factor,
            CompanyShareMA5VsMA10Factor,
            CompanyShareMA20VsMA50Factor,
            CompanyShareTrendSlope20DFactor,
            CompanyShareTrendSlope50DFactor,
            CompanyShareMomentumSlope20DFactor,
            CompanyShareDistanceFrom5MHighFactor,
            CompanyShareDrawdownFrom5MHighFactor,
            CompanyShareDaysSince5MHighFactor,
            CompanyShareShortTermMomentumFactor,
            CompanyShareMediumTermMomentumFactor,
            CompanyShareMomentumZScore20DFactor,
        ]

        specs = []
        for factor_cls, grp in (
            [(f, "return") for f in return_factors]
            + [(f, "risk") for f in risk_factors]
            + [(f, "momentum") for f in momentum_factors]
        ):
            specs.append(
                DependencySpec(
                    factor_type=factor_cls,
                    group=grp,
                    frequency=DependencySpec.SELF,
                    source_in=["calculated"],
                )
            )
        return specs

    def calculate(self, dependencies: dict) -> Optional[float]:
        """Return LightGBM quintile rank (1.0–5.0) or None."""
        if self._provider is None:
            return None
        entity = dependencies.get("entity")
        target_date = dependencies.get("target_date")
        if entity is None or target_date is None:
            return None
        return self._provider.predict(dependencies, entity, target_date)
