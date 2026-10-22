"""
src/domain/entities/factor/dependency_spec.py

DependencySpec — rich descriptor for a dynamic factor dependency.

Usage in calculate_dependencies:
    @property
    def calculate_dependencies(self) -> list:
        return [
            DependencySpec(
                factor_type=CompanyShareFactor,
                group="price",
                frequency=DependencySpec.SELF,          # inherit from parent
                source_not_in=["calculated"],
            )
        ]

The resolution service detects DependencySpec instances and:
  1. Resolves SELF sentinels from the parent factor's own attributes.
  2. Queries all factor records of factor_type from the repo.
  3. Filters them by the resolved parameter constraints.
  4. Resolves a FactorValue for each matching factor × related entity.
  5. Returns a list of values keyed by factor_type.__name__ in dependency_values.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import ClassVar, Any, List, Optional

_SELF = object()


@dataclass
class DependencySpec:
    """Specification for a dynamic factor dependency with parameter filtering."""

    factor_type: type

    # Exact-match filters.  Use DependencySpec.SELF to inherit the value from
    # the parent factor.  Use None to skip filtering on that dimension.
    group: Any = None
    subgroup: Any = None
    frequency: Any = None
    data_type: Any = None
    source: Any = None

    # Whitelist / blacklist filters (applied after exact-match resolution).
    source_in: List[str] = field(default_factory=list)
    source_not_in: List[str] = field(default_factory=list)
    frequency_in: List[str] = field(default_factory=list)
    frequency_not_in: List[str] = field(default_factory=list)
    name_in: List[str] = field(default_factory=list)
    name_not_in: List[str] = field(default_factory=list)

    # History window of a raw (stored) dependency: None = the value at the target date (one value);
    # an int N = the N latest closed bars ending at the target date, oldest first (a series shorter
    # than N is missing data); 'ytd' = the last bar of the previous year + every bar of this year.
    lookback: Any = None

    # Key under which calculate() receives the values (default: the factor type name). Needed when two
    # specs share a factor type, e.g. the highs and the lows of CompanyShareFactor.
    key: Optional[str] = None

    # Resolve the dependency on ANOTHER entity of the parent's class, identified by its symbol (e.g. the SPY
    # share for a share-versus-benchmark factor), instead of the parent entity and its related entities.
    entity_symbol: Optional[str] = None

    # Sentinel — use as a field value to mean "inherit from the parent factor".
    SELF: ClassVar = _SELF

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def result_key(self) -> str:
        """Key of the resolved values in calculate(dependencies)."""
        return self.key or self.dep_name

    @property
    def dep_name(self) -> str:
        """Key used in dependency_values dict and in calculate(dependencies)."""
        return self.factor_type.__name__

    def resolve_params(self, parent_factor) -> dict:
        """Return a dict of resolved parameter constraints.

        Each SELF sentinel is replaced with the corresponding attribute value
        from parent_factor.  None means "no filter on this dimension".
        """
        def _resolve(val, attr):
            return getattr(parent_factor, attr, None) if val is _SELF else val

        return {
            "group":     _resolve(self.group,     "group"),
            "subgroup":  _resolve(self.subgroup,  "subgroup"),
            "frequency": _resolve(self.frequency, "frequency"),
            "data_type": _resolve(self.data_type, "data_type"),
            "source":    _resolve(self.source,    "source"),
        }

    def matches_factor(self, parent_factor, candidate_factor) -> bool:
        """Return True if candidate_factor satisfies every constraint in this spec."""
        params = self.resolve_params(parent_factor)

        # Exact-match constraints (None = no constraint)
        for attr, expected in params.items():
            if expected is not None:
                if getattr(candidate_factor, attr, None) != expected:
                    return False

        # Whitelist / blacklist on source
        candidate_source = getattr(candidate_factor, "source", None)
        if self.source_in and candidate_source not in self.source_in:
            return False
        if self.source_not_in and candidate_source in self.source_not_in:
            return False

        # Whitelist / blacklist on frequency
        candidate_freq = getattr(candidate_factor, "frequency", None)
        if self.frequency_in and candidate_freq not in self.frequency_in:
            return False
        if self.frequency_not_in and candidate_freq in self.frequency_not_in:
            return False

        # Whitelist / blacklist on name
        candidate_name = getattr(candidate_factor, "name", None)
        if self.name_in and candidate_name not in self.name_in:
            return False
        if self.name_not_in and candidate_name in self.name_not_in:
            return False

        return True
