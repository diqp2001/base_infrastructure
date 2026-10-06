"""
CompanyShareSpatioTemporalMomentumFactor — trading signal of the
Spatio-Temporal Momentum model (Tan, Roberts, Zohren 2023) for one
universe constituent.

The model scores the whole universe jointly from an
[assets x lookback x features] tensor, so ``calculate`` delegates to an
injected provider (application layer) that runs the model once per date and
returns the score of the requested constituent.  The domain entity knows
nothing about PyTorch.

Output: float signal (position direction and size before vol scaling).
"""

from typing import Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
    CompanyShareFactor,
)


class CompanyShareSpatioTemporalMomentumFactor(CompanyShareFactor):

    def __init__(
        self,
        name: str = "spatio_temporal_momentum_signal",
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
        # The provider builds the full cross-sectional history itself; the
        # raw daily close of the constituent is declared so the resolver
        # takes the calculate() branch and the value is anchored to an
        # observed (closed) bar.
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [
            DependencySpec(
                factor_type=CompanyShareFactor,
                group="price",
                name_in=["close"],
                source_not_in=["calculated"],
            )
        ]

    def calculate(self, dependencies: dict) -> Optional[float]:
        """Return the model signal for ``dependencies['entity']`` or None."""
        if self._provider is None:
            return None
        entity = dependencies.get("entity")
        target_date = dependencies.get("target_date")
        if entity is None or target_date is None:
            return None
        return self._provider.predict(dependencies, entity, target_date)
