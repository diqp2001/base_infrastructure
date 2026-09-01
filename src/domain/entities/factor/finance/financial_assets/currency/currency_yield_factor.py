"""
CurrencyYieldFactor — the risk-free yield of a Currency asset.

For USD: derived from the CME SR3 (SOFR 3-month) futures annualized yield.
         SR3 price convention F = 100 - R  →  R = (100 - F) / 100.
For CAD: derived from the equivalent CORRA benchmark.

Resolution path:
  1. FactorDependency record links CurrencyYieldFactor → BondFutureAnnualizedYieldFactor.
  2. _handle_missing_dependency calls get_related_entities(currency_id).
  3. get_related_entities maps the currency ISO code via BENCHMARK_MAP to the
     corresponding BondFuture ticker and returns that entity.
  4. resolve_factor_value recurses to fetch BondFutureAnnualizedYieldFactor for that
     bond future and passes the result as {'rate': <value>} to calculate().
"""

from __future__ import annotations
from decimal import Decimal
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.currency.currency_factor import CurrencyFactor


class CurrencyYieldFactor(CurrencyFactor):
    """
    Domain entity representing the risk-free yield of a currency.

    Calculated from the benchmark overnight / short-term rate futures:
      USD → SR3 (CME SOFR 3-month futures)  annualized yield R = (100 - F) / 100
      CAD → CORRA benchmark equivalent

    Dependency name: 'rate' (FactorDependency → BondFutureAnnualizedYieldFactor, lag 1d).
    """

    BENCHMARK_MAP: dict = {'USD': 'SR3', 'CAD': 'CORRA'}

    def __init__(
        self,
        name: str = "currency_yield",
        group: str = "fundamental",
        subgroup: Optional[str] = "yield",
        frequency: Optional[str] = "1d",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = (
            "Risk-free yield derived from benchmark rate futures "
            "(USD→SR3 SOFR, CAD→CORRA). R = (100 - F) / 100."
        ),
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            frequency=frequency,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
        )

    def calculate(self, dependencies: dict) -> Optional[Decimal]:
        """Pass through the benchmark annualized rate unchanged."""
        raw = dependencies.get("BondFutureAnnualizedYieldFactor")
        if raw is None:
            return None
        values = raw if isinstance(raw, list) else [raw]
        valid = [Decimal(str(v)) for v in values if v is not None]
        if not valid:
            return None
        return sum(valid) / len(valid)

    def __repr__(self):
        return (
            f"CurrencyYieldFactor(name={self.name!r}, group={self.group!r}, "
            f"subgroup={self.subgroup!r})"
        )

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_annualized_yield_factor import BondFutureAnnualizedYieldFactor
        return [
            DependencySpec(
                factor_type=BondFutureAnnualizedYieldFactor,
                frequency=DependencySpec.SELF,
                group="return",
                source_in=["calculated"],
            )
        ]
