"""
CompanyShareOptionImpliedVolMlFactor — ML-based implied volatility for a
company share option.

Design
------
* Same three financial dependencies as the analytical IV factor
  (CompanyShareOptionValueFactor, CompanyShareValueFactor,
  CompanyShareOptionRFYieldFactor) resolved via DependencySpec / Branch A.
* calculate() delegates to ImpliedVolMlModelProvider, which handles the full
  lifecycle: regime fingerprinting, artifact lookup, auto-training, prediction.
* The provider is injected by the repository's _to_entity / _create_or_get so
  that the domain entity stays framework-agnostic.
"""

from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import (
    CompanyShareOptionFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_value_factor import (
    CompanyShareOptionValueFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import (
    CompanyShareValueFactor,
)


class CompanyShareOptionImpliedVolMlFactor(CompanyShareOptionFactor):
    """
    ML-predicted implied volatility of a company share option.

    Trained on historical analytical-IV (Newton-Raphson) values; predicts IV
    from market-observable features without solving Black-Scholes numerically.
    """

    def __init__(
        self,
        name: str = "implied_vol_ml",
        group: str = "volatility",
        subgroup: Optional[str] = "implied",
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
        # Provider injected by the repo; None means predict() returns None
        self._provider = provider

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rf_yield_factor import (
            CompanyShareOptionRFYieldFactor,
        )

        return [
            DependencySpec(
                factor_type=CompanyShareOptionValueFactor,
                group="value",
                frequency=DependencySpec.SELF,
                source_in=["calculated"],
            ),
            DependencySpec(
                factor_type=CompanyShareValueFactor,
                group="value",
                frequency=DependencySpec.SELF,
                source_in=["calculated"],
            ),
            DependencySpec(
                factor_type=CompanyShareOptionRFYieldFactor,
                group="fundamental",
                frequency=DependencySpec.SELF,
                source_in=["calculated"],
            ),
        ]

    def calculate(self, dependencies: dict) -> Optional[float]:
        """
        Return ML-predicted implied vol.

        Delegates entirely to ImpliedVolMlModelProvider — no Black-Scholes
        computation here.  Returns None if the provider is unavailable or
        cannot produce a prediction.
        """
        if self._provider is None:
            return None
        entity = dependencies.get("entity")
        target_date = dependencies.get("target_date")
        if entity is None or target_date is None:
            return None
        return self._provider.predict(dependencies, entity, target_date)
