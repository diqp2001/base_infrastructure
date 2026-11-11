"""
src/domain/entities/factor/finance/financial_assets/derivatives/option/etf_share_option/etf_share_option_dispersion_factor.py

Shared mechanics of the ETF option dispersion strategy factors - not a factor of its own (no stored series, no ORM
identity). Each strategy factor is a separate class with its own formula, valued on the ETF option (the short leg):

    ETFShareOptionNetPremiumFactor           premium_<measure>               the strategy's cost
    ETFShareOptionReversePremiumFactor       reverse_premium_<measure>       the strategy reversed (information)
    ETFShareOptionImpliedCorrelationFactor   implied_correlation_<measure>   from the legs' volatilities
    ETFShareOptionScenarioPayoffFactor       scenario_<scenario>_<measure>   payoff at maturity in a scenario

Name: <KIND>_<measure>, the measure one of the class's MEASURES. A stored row whose name is not of that form decodes
with no measure, no dependencies and no value.

Resolution branch A - calculate() receives, at the value's time (the screen's quote time):
    'etf_<field>'           [value]                               the ETF option's quote series (ETFShareOptionFactor)
    'constituent_<field>'   {constituent option symbol: [value]}  the constituent options' series (CompanyShareOptionFactor,
                                                                  per entity)
    'weights'               {constituent option symbol: weight}   the legs in force (the ETF option repository's legs
                                                                  universe, injected by the resolution service)
    'entity'                the ETF option (its option_type gives the right)
for each field the factor reads (fields: the class's FIELDS unless a measure needs fewer). Weights are renormalized over the legs; every leg must have its fields
(MIN_LEG_COVERAGE) - a missing input is never a zero.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import (
    CALL, ETFShareOptionFactor, Leg, QUOTE_SUBGROUP, right_of,
)

MIN_LEG_COVERAGE = 1.0


def _first(values) -> Optional[float]:
    return float(values[0]) if values and values[0] is not None else None


class ETFShareOptionDispersionFactor(ETFShareOptionFactor):
    """Base of the ETF option dispersion strategy factors (see the module docstring). Subclasses set KIND / MEASURES
    / FIELDS and implement measures()."""

    KIND: str = ""
    MEASURES: Tuple[str, ...] = ()
    FIELDS: Tuple[str, ...] = ("bid", "ask", "underlying_price", "strike", "multiplier")

    def __init__(self, name: str, group: str = "dispersion", subgroup: Optional[str] = None,
                 frequency: Optional[str] = "1d", data_type: Optional[str] = "numeric",
                 source: Optional[str] = "calculated", definition: Optional[str] = None,
                 factor_id: Optional[int] = None, **kwargs):
        measure = self.parse_name(name)
        super().__init__(name=name, group=group, subgroup=subgroup or self.KIND, frequency=frequency,
                         data_type=data_type, source=source, factor_id=factor_id,
                         definition=definition or (f"ETF option dispersion {self.KIND.replace('_', ' ')}: "
                                                   f"{measure.replace('_', ' ')}" if measure else name))
        self.measure = measure

    @property
    def fields(self) -> Tuple[str, ...]:
        """The quote fields this factor reads (on the ETF option and on every leg)."""
        return self.FIELDS

    @classmethod
    def factor_name(cls, measure: str) -> str:
        return f"{cls.KIND}_{measure}"

    @classmethod
    def parse_name(cls, name: str) -> Optional[str]:
        prefix = f"{cls.KIND}_"
        if not cls.KIND or not (name or "").startswith(prefix) or name[len(prefix):] not in cls.MEASURES:
            return None
        return name[len(prefix):]

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import (
            CompanyShareOptionFactor,
        )
        if not self.measure:
            return []
        specs = []
        for field in self.fields:
            specs.append(DependencySpec(factor_type=ETFShareOptionFactor, group="price", subgroup=QUOTE_SUBGROUP,
                                        frequency="1d", name_in=[field], key=f"etf_{field}"))
            specs.append(DependencySpec(factor_type=CompanyShareOptionFactor, group="price", subgroup=QUOTE_SUBGROUP,
                                        frequency="1d", name_in=[field], key=f"constituent_{field}", per_entity=True))
        return specs

    def legs(self, dependencies: Dict[str, Any]) -> Optional[Tuple[Leg, List[Leg]]]:
        """The ETF leg and the constituent legs (weights renormalized over the legs), or None when a leg misses a
        field (below MIN_LEG_COVERAGE of the weight)."""
        weights = {s: float(w) for s, w in (dependencies.get("weights") or {}).items() if w is not None and float(w) > 0}
        entity = dependencies.get("entity")
        right = right_of(getattr(entity, "option_type", None)) if entity is not None else CALL
        if not weights or right is None:
            return None
        fields = self.fields
        etf_quote = {f: _first(dependencies.get(f"etf_{f}")) for f in fields}
        etf = self.leg("ETF", etf_quote, 1.0, right)
        quotes = {s: {f: _first((dependencies.get(f"constituent_{f}") or {}).get(s)) for f in fields}
                  for s in weights}
        complete = {s: q for s, q in quotes.items() if all(q[f] is not None for f in fields)}
        total, covered = sum(weights.values()), sum(weights[s] for s in complete)
        if etf is None or any(v is None for v in etf_quote.values()):
            return None
        if covered <= 0 or covered / total + 1e-12 < MIN_LEG_COVERAGE:
            return None
        legs = [self.leg(s, q, weights[s] / covered, right) for s, q in complete.items()]
        if any(leg is None for leg in legs):
            return None
        return etf, legs

    def measures(self, etf: Leg, constituents: List[Leg]) -> Dict[str, Optional[float]]:
        raise NotImplementedError

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        if not self.measure:
            return None
        legs = self.legs(dependencies)
        if legs is None:
            return None
        return self.measures(*legs).get(self.measure)
