"""
src/application/services/data/entities/factor/factor_value_batch_resolution_service.py

Batch-oriented factor value resolver.

Architecture
============
This service sits *above* FactorValueResolutionService in the call stack::

    FactorValueBatchResolutionService
        ├── build dependency graph  (BFS from root factor, stored + dynamic deps)
        ├── iterative DFS — cycle detection + topological sort
        ├── per-factor date-set computation (respects FactorDependency.lag)
        └── batch orchestration  →  for each factor in dependency-first order,
                                    resolve for ALL entities × ALL dates
                                        ↓
                                    FactorValueResolutionService.resolve_factor_value
                                    (existing single-entity mechanics: check DB, IBKR, calculate)

Why batch ordering matters
==========================
The existing ``resolve_factor_value`` recursively resolves dependencies per entity::

    resolve(A, entity1) → recurse into resolve(B, entity1)
    resolve(A, entity2) → recurse into resolve(B, entity2)

This recomputes B for each entity and recurses into B's own deps again for
each one.  The batch service avoids this by:

1. Running B for ALL entities first and persisting results to DB.
2. Then running A for ALL entities — A's ``_check_existing_value`` finds B's
   results in DB immediately, making the recursion terminate at depth 1.

Shared dependencies (diamond graphs) are deduplicated automatically: a factor
that appears once in the topological order is computed once.

Cycle detection
===============
DFS uses three states: UNVISITED → VISITING → VISITED.
Encountering a VISITING node (back edge) means a cycle.
The full cycle path is reconstructed from the DFS call stack and reported via
``FactorDependencyCycleError``.  The DFS is *iterative* (not recursive) to
avoid Python stack-depth issues on deep graphs.

Dependency lag
==============
Each ``FactorDependency`` carries an optional ``lag: timedelta``.  The batch
service propagates lag-adjusted date sets backwards through the topological
order so that dependency factors are resolved at the correct shifted dates
before their dependents need them.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

from src.application.services.data.entities.factor.exceptions import (
    FactorDependencyCycleError,
)
from src.application.services.data.entities.factor.factor_value_resolution_service import (
    FactorValueResolutionService,
)
from src.domain.entities.factor.factor import Factor
from src.domain.entities.factor.factor_value import FactorValue


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class BatchResolutionResult:
    """
    Result of a ``FactorValueBatchResolutionService.resolve_batch`` call.

    Attributes
    ----------
    requested_factor : Factor
        The root factor that was requested.
    execution_order : list of Factor
        Factors in the dependency-first order they were resolved in.
    resolved_values : dict[int, list[FactorValue]]
        factor_id → successfully resolved FactorValues.
    failed : dict[int, list[tuple]]
        factor_id → list of (entity_id, date) pairs that could not be resolved.
    """

    requested_factor: Factor
    execution_order: List[Factor]
    resolved_values: Dict[int, List[FactorValue]] = field(default_factory=dict)
    failed: Dict[int, List[Tuple]] = field(default_factory=dict)

    @property
    def total_resolved(self) -> int:
        return sum(len(v) for v in self.resolved_values.values())

    @property
    def total_failed(self) -> int:
        return sum(len(v) for v in self.failed.values())

    def values_for_factor(self, factor_id: int) -> List[FactorValue]:
        return self.resolved_values.get(factor_id, [])


# ---------------------------------------------------------------------------
# DFS state
# ---------------------------------------------------------------------------

class _NodeState(Enum):
    UNVISITED = auto()
    VISITING = auto()
    VISITED = auto()


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class FactorValueBatchResolutionService:
    """
    Resolves a factor for multiple entities and dates in dependency-first order.

    Parameters
    ----------
    factory : RepositoryFactory
        Provides access to all repositories.
    logger : logging.Logger, optional
        Caller-supplied logger; a module-level logger is used if omitted.
    """

    def __init__(self, factory, logger: Optional[logging.Logger] = None) -> None:
        self.factory = factory
        self.logger = logger or logging.getLogger(__name__)
        self._resolver = FactorValueResolutionService(
            factory=factory, logger=self.logger
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_batch(
        self,
        factor_entity: Factor,
        entities: List[Any],
        target_dates: List[datetime],
        repository_type: str = "local",
        **kwargs: Any,
    ) -> BatchResolutionResult:
        """
        Resolve a factor for multiple entities and dates.

        Steps
        -----
        1. BFS from ``factor_entity`` to build the full dependency graph
           (stored ``FactorDependency`` rows + ``calculate_dependencies`` props).
        2. Iterative DFS: topological sort with cycle detection.
        3. Compute per-factor date sets, accounting for ``FactorDependency.lag``.
        4. For each factor in dependency-first order, call
           ``resolve_factor_value`` for every (entity, date) pair.

        Parameters
        ----------
        factor_entity : Factor
            The root factor to resolve.
        entities : list
            Domain entity objects; each must expose an ``id`` attribute.
        target_dates : list of datetime
            Dates to resolve the root factor for.
        repository_type : str
            ``"local"`` or ``"ibkr"``.

        Returns
        -------
        BatchResolutionResult

        Raises
        ------
        FactorDependencyCycleError
            If the dependency graph contains a directed cycle.
        """
        self.logger.info(
            "resolve_batch: factor='%s' (id=%s), entities=%d, dates=%d",
            factor_entity.name,
            factor_entity.id,
            len(entities),
            len(target_dates),
        )

        nodes, edges, stored_deps_map = self._build_dependency_graph(factor_entity)

        self.logger.debug(
            "Dependency graph: %d node(s), %d total edge(s)",
            len(nodes),
            sum(len(v) for v in edges.values()),
        )

        execution_order_ids = self._topological_sort(nodes, edges, factor_entity.id)

        self.logger.debug(
            "Execution order: %s",
            " → ".join(nodes[fid].name for fid in execution_order_ids),
        )

        factor_dates = self._compute_factor_date_sets(
            execution_order_ids, target_dates, stored_deps_map
        )

        result = BatchResolutionResult(
            requested_factor=factor_entity,
            execution_order=[nodes[fid] for fid in execution_order_ids],
        )

        for factor_id in execution_order_ids:
            factor = nodes[factor_id]
            dates_for_factor = sorted(factor_dates.get(factor_id, set()))

            self.logger.debug(
                "Resolving '%s': %d entities × %d dates",
                factor.name,
                len(entities),
                len(dates_for_factor),
            )

            resolved, failed = self._resolve_factor_for_batch(
                factor, entities, dates_for_factor, repository_type, **kwargs
            )

            result.resolved_values[factor_id] = resolved
            if failed:
                result.failed[factor_id] = failed

            self.logger.info(
                "'%s': resolved=%d  failed=%d",
                factor.name,
                len(resolved),
                len(failed),
            )

        return result

    # ------------------------------------------------------------------
    # Graph construction (BFS)
    # ------------------------------------------------------------------

    def _build_dependency_graph(
        self,
        root_factor: Factor,
    ) -> Tuple[Dict[int, Factor], Dict[int, List[int]], Dict[int, list]]:
        """
        BFS from *root_factor* to discover the complete dependency sub-graph.

        Returns
        -------
        nodes : dict[factor_id, Factor]
        edges : dict[factor_id, list[factor_id]]
            Direction: dependent → list of independent factor IDs.
        stored_deps_map : dict[factor_id, list[FactorDependency]]
            Stored ``FactorDependency`` objects for lag-adjusted date propagation.
        """
        nodes: Dict[int, Factor] = {}
        edges: Dict[int, List[int]] = {}
        stored_deps_map: Dict[int, list] = {}

        dep_repo = self.factory.factor_dependency_local_repo
        factor_repo = self.factory.factor_local_repo

        queue: List[Factor] = [root_factor]

        while queue:
            factor = queue.pop(0)
            factor_id = factor.id

            if factor_id in nodes:
                continue  # already discovered

            nodes[factor_id] = factor
            edges[factor_id] = []
            stored_deps_map[factor_id] = []

            # 1. Stored dependencies (FactorDependency table)
            try:
                stored_deps = dep_repo.get_by_dependent_factor_id(factor_id) or []
            except Exception as exc:
                self.logger.warning(
                    "Could not fetch stored deps for factor %s: %s", factor_id, exc
                )
                stored_deps = []

            stored_deps_map[factor_id] = list(stored_deps)

            for dep in stored_deps:
                dep_factor: Optional[Factor] = None
                try:
                    dep_factor = factor_repo.get_by_id(dep.independent_factor_id)
                except Exception as exc:
                    self.logger.warning(
                        "Could not load dep factor %s: %s",
                        dep.independent_factor_id,
                        exc,
                    )

                if dep_factor is not None and dep_factor.id is not None:
                    if dep_factor.id not in edges[factor_id]:
                        edges[factor_id].append(dep_factor.id)
                    queue.append(dep_factor)

            # 2. Dynamic dependencies (factor.calculate_dependencies property)
            for dep_factor in self._collect_dynamic_dep_factors(factor):
                if dep_factor.id is not None and dep_factor.id not in edges[factor_id]:
                    edges[factor_id].append(dep_factor.id)
                    queue.append(dep_factor)

        return nodes, edges, stored_deps_map

    def _collect_dynamic_dep_factors(self, factor: Factor) -> List[Factor]:
        """
        Resolve the factor's ``calculate_dependencies`` property to concrete
        Factor objects for graph-building purposes.

        Handles both string names and ``DependencySpec`` objects.
        Returns an empty list for factors without the property.
        """
        if not hasattr(factor, "calculate_dependencies"):
            return []

        try:
            specs = factor.calculate_dependencies
        except Exception:
            return []

        if specs is None:
            return []

        if not isinstance(specs, list):
            specs = [specs]

        result: List[Factor] = []
        all_factors_cache: Optional[List[Factor]] = None

        for spec in specs:
            if isinstance(spec, str):
                try:
                    f = self.factory.factor_local_repo.get_by_name(spec)
                    if f is not None:
                        result.append(f)
                except Exception as exc:
                    self.logger.debug(
                        "Could not resolve string dep '%s': %s", spec, exc
                    )
            else:
                # DependencySpec — filter all known factors
                try:
                    if all_factors_cache is None:
                        all_factors_cache = self.factory.factor_local_repo.get_all() or []
                    for f in all_factors_cache:
                        if (
                            f is not None
                            and hasattr(spec, "matches_factor")
                            and spec.matches_factor(f)
                        ):
                            result.append(f)
                except Exception as exc:
                    self.logger.debug(
                        "Could not resolve DependencySpec %r: %s", spec, exc
                    )

        return result

    # ------------------------------------------------------------------
    # DFS topological sort with cycle detection
    # ------------------------------------------------------------------

    def _topological_sort(
        self,
        nodes: Dict[int, Factor],
        edges: Dict[int, List[int]],
        root_id: int,
    ) -> List[int]:
        """
        Iterative DFS topological sort of the subgraph reachable from *root_id*.

        Returns factor IDs in dependency-first order (leaves first, root last).

        Raises
        ------
        FactorDependencyCycleError
            On any back edge (cycle detected).

        Notes
        -----
        Three-state model: UNVISITED → VISITING → VISITED.
        A *back edge* — encountering a VISITING node — signals a cycle.
        The DFS is iterative to avoid Python stack-depth limits on deep graphs.
        """
        if root_id not in nodes:
            return []

        states: Dict[int, _NodeState] = {
            fid: _NodeState.UNVISITED for fid in nodes
        }
        postorder: List[int] = []

        self._dfs(root_id, nodes, edges, states, postorder)

        return postorder

    def _dfs(
        self,
        root_id: int,
        nodes: Dict[int, Factor],
        edges: Dict[int, List[int]],
        states: Dict[int, _NodeState],
        postorder: List[int],
    ) -> None:
        """
        Single iterative DFS pass starting from *root_id*.

        *path* tracks the current DFS call stack for cycle-path reconstruction.
        *stack* mirrors the implicit call stack: each entry is a
        ``(factor_id, children_iterator)`` pair.  The iterator is stored in the
        tuple so its position is preserved across outer-loop iterations.
        """
        if states.get(root_id, _NodeState.UNVISITED) != _NodeState.UNVISITED:
            return

        path: List[int] = []  # current DFS path (for cycle path reconstruction)
        states[root_id] = _NodeState.VISITING
        path.append(root_id)
        stack: List[Tuple[int, Any]] = [
            (root_id, iter(edges.get(root_id, [])))
        ]

        while stack:
            fid, children = stack[-1]

            advanced = False
            for child_id in children:
                # ``children`` is a persistent iterator — iterating one element
                # here and breaking preserves the position for the next outer
                # loop turn (when we return to this stack frame).
                child_state = states.get(child_id, _NodeState.UNVISITED)

                if child_state == _NodeState.VISITING:
                    # Back edge → cycle detected.
                    cycle_start = path.index(child_id)
                    cycle_ids = path[cycle_start:] + [child_id]
                    cycle_names = [
                        nodes[x].name if x in nodes else str(x)
                        for x in cycle_ids
                    ]
                    raise FactorDependencyCycleError(
                        cycle_names=cycle_names,
                        cycle_ids=cycle_ids,
                    )

                if child_state == _NodeState.UNVISITED and child_id in nodes:
                    # Unexplored child → push onto stack and explore.
                    states[child_id] = _NodeState.VISITING
                    path.append(child_id)
                    stack.append((child_id, iter(edges.get(child_id, []))))
                    advanced = True
                    break

                # VISITED or not in nodes → skip silently.

            if not advanced:
                # All children of *fid* have been processed → finish node.
                stack.pop()
                path.pop()
                states[fid] = _NodeState.VISITED
                postorder.append(fid)

    # ------------------------------------------------------------------
    # Per-factor date-set computation (handles stored-dep lags)
    # ------------------------------------------------------------------

    def _compute_factor_date_sets(
        self,
        execution_order: List[int],
        target_dates: List[datetime],
        stored_deps_map: Dict[int, list],
    ) -> Dict[int, Set[datetime]]:
        """
        Compute, for each factor in the graph, the set of dates that must be
        resolved so that all stored-dependency lag offsets are satisfied.

        Works backwards through the execution order (root → leaves direction)
        propagating lag-adjusted dates to dependency factors.

        Example
        -------
        If A depends on B with lag=1d and target_dates=[T], then B must be
        computed at [T-1d] (weekend-adjusted) so that A can read B's value
        at the lag-adjusted date.
        """
        factor_dates: Dict[int, Set[datetime]] = {}

        # Root factor (last in execution order) uses the caller's target_dates.
        root_id = execution_order[-1]
        factor_dates[root_id] = set(target_dates)

        # Walk from root toward leaves, propagating lag-adjusted dates.
        for factor_id in reversed(execution_order):
            if factor_id not in factor_dates:
                factor_dates[factor_id] = set()

            dates_for_factor = factor_dates[factor_id]
            if not dates_for_factor:
                continue

            for dep in stored_deps_map.get(factor_id, []):
                dep_id = dep.independent_factor_id
                lag: timedelta = getattr(dep, "lag", None) or timedelta(0)

                if dep_id not in factor_dates:
                    factor_dates[dep_id] = set()

                for d in dates_for_factor:
                    factor_dates[dep_id].add(self._apply_lag(d, lag))

        # Ensure every factor in the graph has at least the target_dates as a
        # fallback (covers dynamic deps whose lag we cannot know statically).
        for factor_id in execution_order:
            if not factor_dates.get(factor_id):
                factor_dates[factor_id] = set(target_dates)

        return factor_dates

    @staticmethod
    def _apply_lag(dt: datetime, lag: timedelta) -> datetime:
        """
        Subtract *lag* from *dt*, stepping back over weekends (Sat/Sun).

        Mirrors the weekend-skip logic in
        ``FactorValueResolutionService._resolve_stored_dependencies``.
        """
        if not lag or lag.total_seconds() == 0:
            return dt
        result = dt - lag
        while result.weekday() >= 5:  # 5=Saturday, 6=Sunday
            result -= timedelta(days=1)
        return result

    # ------------------------------------------------------------------
    # Batch execution for a single factor
    # ------------------------------------------------------------------

    def _resolve_factor_for_batch(
        self,
        factor: Factor,
        entities: List[Any],
        dates: List[datetime],
        repository_type: str,
        **kwargs: Any,
    ) -> Tuple[List[FactorValue], List[Tuple]]:
        """
        Resolve a single factor for every (entity, date) pair.

        Delegates to ``FactorValueResolutionService.resolve_factor_value``.
        Because dependency factors have already been processed and their values
        persisted to DB in prior iterations of the execution-order loop, the
        existing resolver's ``_check_existing_value`` call short-circuits
        immediately when looking up pre-computed dependency values, so the
        per-entity recursion terminates at depth 1.

        Returns
        -------
        resolved : list of FactorValue
        failed   : list of (entity_id, date) tuples
        """
        resolved: List[FactorValue] = []
        failed: List[Tuple] = []

        for entity in entities:
            for date in dates:
                try:
                    fv = self._resolver.resolve_factor_value(
                        factor_entity=factor,
                        entity=entity,
                        time_date=date,
                        repository_type=repository_type,
                        **kwargs,
                    )
                    if fv is not None:
                        resolved.append(fv)
                    else:
                        failed.append((getattr(entity, "id", None), date))
                except FactorDependencyCycleError:
                    raise  # propagate; caller should not have reached here
                except Exception as exc:
                    entity_id = getattr(entity, "id", None)
                    self.logger.debug(
                        "Failed to resolve '%s' for entity=%s date=%s: %s",
                        factor.name,
                        entity_id,
                        date,
                        exc,
                    )
                    failed.append((entity_id, date))

        return resolved, failed
