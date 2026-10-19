"""
FactorDependencyExplainer — why a factor value is missing, as a tree of its dependencies.

For a factor that did not resolve for an entity at a time, walk its declared dependencies the way
FactorValueResolutionService does (same related entities, same DependencySpec matching) and report,
for every node, the value found or the reason it is missing:

    no stored definition matches the spec      (with the stored definitions, e.g. their frequency)
    no related entity                         (with a hint, e.g. the dated SOFR contract of a currency)
    no stored observation at or before t      (with the latest stored observation)
    dependency resolved / missing             (recursing into the missing ones)

Values are obtained through resolve_factor_value, exactly as in a run (a resolved dependency is stored
as it would have been). The walk is bounded (depth, visited nodes).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional

from src.domain.entities.factor.dependency_spec import DependencySpec


@dataclass
class DependencyNode:
    factor: str                                   # factor class / definition name
    entity: str                                   # "Type:id symbol"
    value: Optional[float] = None
    status: str = "ok"                            # ok | missing | no_definition | no_related_entity | no_observation | error
    detail: str = ""
    children: List["DependencyNode"] = field(default_factory=list)

    @property
    def missing(self) -> bool:
        return self.status != "ok"

    def root_causes(self) -> List["DependencyNode"]:
        """Deepest missing nodes (the reasons), in walk order."""
        if not self.missing:
            return []
        below = [cause for child in self.children for cause in child.root_causes()]
        return below or [self]

    def render(self, indent: str = "") -> str:
        lines = [f"{self.factor}  [{self.entity}]  " + (f"= {self.value:.6g}" if not self.missing
                                                        else f"MISSING ({self.status})" + (f": {self.detail}" if self.detail else ""))]
        for i, child in enumerate(self.children):
            last = i == len(self.children) - 1
            sub = child.render(indent + ("   " if last else "│  "))
            lines.append(indent + ("└─ " if last else "├─ ") + sub)
        return "\n".join(lines)


def entity_label(entity) -> str:
    symbol = getattr(entity, "symbol", None) or getattr(entity, "name", None) or ""
    return f"{type(entity).__name__.removesuffix('Model')}:{getattr(entity, 'id', '?')} {symbol}".strip()


class FactorDependencyExplainer:

    def __init__(self, resolver, factory, max_depth: int = 6):
        self.resolver = resolver
        self.factory = factory
        self.max_depth = max_depth

    # ------------------------------------------------------------------ public
    def explain(self, factor_definition, entity, time: datetime) -> DependencyNode:
        """Tree for `factor_definition` on `entity` at `time` (the root's own value is resolved too)."""
        return self._node(factor_definition, entity, time, depth=0, visited=set())

    # ------------------------------------------------------------------ walk
    def _node(self, definition, entity, time, depth, visited) -> DependencyNode:
        name = getattr(definition, "name", None) or type(definition).__name__
        label = f"{type(definition).__name__.removesuffix('Model')} '{name}'"
        node = DependencyNode(factor=label, entity=entity_label(entity))
        key = (getattr(definition, "id", None), type(entity).__name__, getattr(entity, "id", None))
        value = self._value(definition, entity, time)
        if value is not None:
            node.value = value
            return node
        node.status = "missing"
        if key in visited or depth >= self.max_depth:
            node.detail = "not expanded (cycle or depth limit)"
            return node
        visited = visited | {key}

        deps = self._dependencies(definition)
        if not deps:
            node.status = "no_observation"
            node.detail = self._observation_detail(definition, entity, time)
            return node
        targets = self._targets(entity, time)
        parent = self._domain(definition)
        for dep in deps:
            node.children.extend(self._dependency_nodes(dep, parent, entity, targets, time, depth, visited))
        if node.children and all(not c.missing for c in node.children):
            node.detail = "every dependency resolved: calculate() returned no value with these inputs"
        return node

    def _dependency_nodes(self, dep, parent, entity, targets, time, depth, visited) -> List[DependencyNode]:
        dep_name = dep if isinstance(dep, str) else dep.dep_name
        repo = self.factory.get_local_repository(dep_name) if self.factory else None

        if isinstance(dep, str) and (repo is None or not hasattr(repo, "get_factor_entity")):
            value = self._entity_attribute(dep, entity)                  # e.g. 'Position'
            node = DependencyNode(factor=f"{dep} (entity attribute)", entity=entity_label(entity), value=value)
            if value is None:
                node.status, node.detail = "missing", f"no related {dep} with a numeric value"
            return [node]

        definitions = self._definitions(dep, parent, repo)
        if not definitions:
            stored = ", ".join(f"'{getattr(d, 'name', '?')}' freq={getattr(d, 'frequency', None)} "
                               f"source={getattr(d, 'source', None)}" for d in (self._all(repo) or [])[:6])
            wanted = self._spec_text(dep, parent)
            return [DependencyNode(factor=dep_name, entity=entity_label(entity), status="no_definition",
                                   detail=f"no stored definition matches {wanted}; stored: [{stored or 'none'}]")]

        nodes = []
        for definition in definitions[:3]:
            dep_targets = self._targets_for(definition, targets)
            if not dep_targets:
                nodes.append(DependencyNode(
                    factor=f"{dep_name} '{getattr(definition, 'name', '?')}'", entity=entity_label(entity),
                    status="no_related_entity", detail=self._related_hint(entity, dep_name, time)))
                continue
            for target in dep_targets[:4]:
                nodes.append(self._node(definition, target, time, depth + 1, visited))
        return nodes

    # ------------------------------------------------------------------ helpers
    def _value(self, definition, entity, time) -> Optional[float]:
        try:
            fv = self.resolver.resolve_factor_value(definition, entity, time)
            return None if fv is None or fv.value is None else float(fv.value)
        except Exception:
            return None

    def _domain(self, definition):
        """The domain factor for a stored definition: repositories may return ORM rows, which do not
        carry calculate_dependencies. Rebuilt from the type's repository, with the stored attributes."""
        if hasattr(type(definition), "calculate_dependencies"):
            return definition
        key = type(definition).__name__.removesuffix("Model")
        try:
            repo = self.factory.get_local_repository(key)
            domain = repo.get_factor_entity()()
        except Exception:
            return definition
        for attr in ("id", "name", "group", "subgroup", "frequency", "data_type", "source"):
            value = getattr(definition, attr, None)
            if value is not None:
                try:
                    setattr(domain, attr, value)
                except Exception:
                    pass
        return domain

    def _dependencies(self, definition) -> list:
        try:
            deps = getattr(self._domain(definition), "calculate_dependencies", None)
        except Exception:
            return []
        if deps is None:
            return []
        return deps if isinstance(deps, list) else [deps]

    def _targets(self, entity, time) -> list:
        try:
            return self.resolver._get_resolution_entities(entity, getattr(entity, "id", None), "local",
                                                          target_date=time)
        except Exception:
            return [entity]

    def _targets_for(self, definition, targets) -> list:
        try:
            return self.resolver._dependency_targets(definition, targets)
        except Exception:
            return targets

    @staticmethod
    def _all(repo) -> list:
        try:
            return repo.get_all() or [] if repo is not None and hasattr(repo, "get_all") else []
        except Exception:
            return []

    def _definitions(self, dep, parent, repo) -> list:
        if isinstance(dep, DependencySpec):
            return [d for d in self._all(repo) if dep.matches_factor(parent, d)]
        try:                                                              # string dep: built from defaults
            defaults = repo.get_factor_entity()()
            found = repo._create_or_get(repo.get_factor_entity(), primary_key=defaults.name,
                                        group=defaults.group, subgroup=defaults.subgroup,
                                        data_type=defaults.data_type, frequency=defaults.frequency)
            return [found] if found is not None else []
        except Exception:
            return []

    @staticmethod
    def _spec_text(dep, parent) -> str:
        if not isinstance(dep, DependencySpec):
            return f"'{dep}'"
        params = {k: v for k, v in dep.resolve_params(parent).items() if v is not None}
        extra = {k: v for k, v in (("source_in", dep.source_in), ("source_not_in", dep.source_not_in),
                                    ("name_in", dep.name_in)) if v}
        return f"{dep.dep_name}({', '.join(f'{k}={v}' for k, v in {**params, **extra}.items())})"

    def _entity_attribute(self, name, entity) -> Optional[float]:
        try:
            return self.resolver._resolve_entity_attr_dep(name, entity)
        except Exception:
            return None

    def _observation_detail(self, definition, entity, time) -> str:
        repo = getattr(self.factory, "factor_value_local_repo", None)
        latest = None
        try:
            latest = repo.get_most_recent_before(getattr(definition, "id", None), getattr(entity, "id", None),
                                                 time.strftime("%Y-%m-%d %H:%M:%S"))
        except Exception:
            pass
        if latest is None:
            return f"no stored observation at or before {time} (raw data never imported for this entity)"
        return (f"no usable observation at {time}: latest stored {latest.date} = {latest.value} "
                f"(too old, or the bar had not closed)")

    def _related_hint(self, entity, dep_name, time) -> str:
        text = f"{entity_label(entity)} has no related entity for {dep_name} at {time}"
        if type(entity).__name__.removesuffix("Model") == "Currency":
            try:
                from src.domain.entities.factor.finance.financial_assets.currency.currency_yield_factor import (
                    CurrencyYieldFactor,
                )
                from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.future.bond_future_repository import (
                    BondFutureRepository,
                )
                root = CurrencyYieldFactor.BENCHMARK_MAP.get(str(getattr(entity, "symbol", "")).upper())
                if root:
                    symbol = BondFutureRepository.front_month_symbol(root, time.date())
                    text += (f" — the benchmark future of that date is {symbol}: not stored locally and not "
                             f"returned by IBKR (add it to the universe)")
            except Exception:
                pass
        return text
