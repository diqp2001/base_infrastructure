"""
tests/test_factor_value_batch_resolution.py

Comprehensive tests for FactorValueBatchResolutionService:

Coverage
--------
Exception class                     TestFactorDependencyCycleError
Topological sort — acyclic graphs   TestTopologicalSortAcyclic
Cycle detection                     TestCycleDetection
Dependency graph construction       TestDependencyGraphBuilding
Date-set propagation                TestDateSetComputation
Batch execution ordering            TestBatchExecutionOrder
Shared-dependency deduplication     TestSharedDependencyDeduplication
Dynamic dependency cycles           TestDynamicDependencyCycles
"""

import unittest
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Any, List, Optional
from unittest.mock import MagicMock, patch, call

from src.application.services.data.entities.factor.exceptions import (
    FactorDependencyCycleError,
    FactorResolutionError,
)
from src.application.services.data.entities.factor.factor_value_batch_resolution_service import (
    BatchResolutionResult,
    FactorValueBatchResolutionService,
    _NodeState,
)


# ---------------------------------------------------------------------------
# Minimal mock domain objects (no SQLAlchemy required)
# ---------------------------------------------------------------------------

class _MockFactor:
    """Lightweight stand-in for a Factor domain entity."""
    def __init__(self, factor_id: int, name: str):
        self.id = factor_id
        self.name = name


class _MockFactorWithDynDeps(_MockFactor):
    """Factor that exposes calculate_dependencies (Branch A)."""
    def __init__(self, factor_id: int, name: str, dep_names: List[str]):
        super().__init__(factor_id, name)
        self.calculate_dependencies = dep_names


@dataclass
class _MockDep:
    """Minimal FactorDependency stand-in."""
    dependent_factor_id: int
    independent_factor_id: int
    lag: Optional[timedelta] = None
    dependency_name: Optional[str] = None


class _MockEntity:
    """Stand-in for a domain entity (CompanyShare etc.)."""
    def __init__(self, entity_id: int):
        self.id = entity_id


class _MockFactorValue:
    """Stand-in for FactorValue domain object."""
    def __init__(self, factor_id: int, entity_id: int, date: datetime):
        self.factor_id = factor_id
        self.entity_id = entity_id
        self.date = date


def _make_service_with_mocked_factory(
    stored_deps_by_factor: Optional[dict] = None,
    factors_by_id: Optional[dict] = None,
    factors_by_name: Optional[dict] = None,
    all_factors: Optional[list] = None,
) -> FactorValueBatchResolutionService:
    """
    Build a FactorValueBatchResolutionService with a mocked factory.

    Parameters
    ----------
    stored_deps_by_factor : dict[factor_id → list[_MockDep]]
        Simulates factor_dependency_local_repo.get_by_dependent_factor_id.
    factors_by_id : dict[factor_id → _MockFactor]
        Simulates factor_local_repo.get_by_id.
    factors_by_name : dict[name → _MockFactor]
        Simulates factor_local_repo.get_by_name.
    all_factors : list[_MockFactor]
        Simulates factor_local_repo.get_all.
    """
    stored_deps_by_factor = stored_deps_by_factor or {}
    factors_by_id = factors_by_id or {}
    factors_by_name = factors_by_name or {}
    all_factors = all_factors or []

    factory = MagicMock()
    factory.factor_dependency_local_repo.get_by_dependent_factor_id.side_effect = (
        lambda fid: stored_deps_by_factor.get(fid, [])
    )
    factory.factor_local_repo.get_by_id.side_effect = (
        lambda fid: factors_by_id.get(fid)
    )
    factory.factor_local_repo.get_by_name.side_effect = (
        lambda name: factors_by_name.get(name)
    )
    factory.factor_local_repo.get_all.return_value = all_factors

    # The FactorValueResolutionService constructor references factory heavily;
    # patch it out so we can control resolve_factor_value directly.
    with patch(
        "src.application.services.data.entities.factor"
        ".factor_value_batch_resolution_service.FactorValueResolutionService"
    ) as mock_resolver_cls:
        mock_resolver_cls.return_value = MagicMock()
        svc = FactorValueBatchResolutionService(factory=factory)

    return svc


# ===========================================================================
# 1. Exception class
# ===========================================================================

class TestFactorDependencyCycleError(unittest.TestCase):

    def test_is_subclass_of_factor_resolution_error(self):
        err = FactorDependencyCycleError(["A", "A"])
        self.assertIsInstance(err, FactorResolutionError)

    def test_is_exception(self):
        err = FactorDependencyCycleError(["A", "A"])
        self.assertIsInstance(err, Exception)

    def test_cycle_path_self_cycle(self):
        err = FactorDependencyCycleError(["A", "A"])
        self.assertEqual(err.cycle_path, "A → A")

    def test_cycle_path_two_factor(self):
        err = FactorDependencyCycleError(["A", "B", "A"])
        self.assertEqual(err.cycle_path, "A → B → A")

    def test_cycle_path_three_factor(self):
        err = FactorDependencyCycleError(["A", "B", "C", "A"])
        self.assertEqual(err.cycle_path, "A → B → C → A")

    def test_cycle_names_stored(self):
        names = ["X", "Y", "Z", "X"]
        err = FactorDependencyCycleError(names)
        self.assertEqual(err.cycle_names, names)

    def test_cycle_ids_stored(self):
        err = FactorDependencyCycleError(["A", "B", "A"], cycle_ids=[1, 2, 1])
        self.assertEqual(err.cycle_ids, [1, 2, 1])

    def test_cycle_ids_defaults_to_empty(self):
        err = FactorDependencyCycleError(["A", "A"])
        self.assertEqual(err.cycle_ids, [])

    def test_str_contains_path(self):
        err = FactorDependencyCycleError(["A", "B", "A"])
        self.assertIn("A → B → A", str(err))

    def test_custom_message(self):
        err = FactorDependencyCycleError(["A", "A"], message="custom msg")
        self.assertEqual(str(err), "custom msg")

    def test_raises_as_exception(self):
        with self.assertRaises(FactorDependencyCycleError) as ctx:
            raise FactorDependencyCycleError(["P", "Q", "P"])
        self.assertIn("P → Q → P", str(ctx.exception))


# ===========================================================================
# 2. Topological sort — acyclic graphs
#    (_topological_sort tested directly with mock nodes + edges dicts)
# ===========================================================================

class TestTopologicalSortAcyclic(unittest.TestCase):

    def _sort(self, factors, edges, root_id):
        """Helper: build service, call _topological_sort, return names."""
        svc = _make_service_with_mocked_factory()
        nodes = {f.id: f for f in factors}
        order_ids = svc._topological_sort(nodes, edges, root_id)
        return [nodes[fid].name for fid in order_ids]

    def test_no_dependencies_single_factor(self):
        """Factor with no deps → execution order is just itself."""
        a = _MockFactor(1, "A")
        order = self._sort([a], {1: []}, root_id=1)
        self.assertEqual(order, ["A"])

    def test_one_dependency(self):
        """A → B (A depends on B) → execution order: [B, A]."""
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        # edge: A has B as dependency
        order = self._sort([a, b], {1: [2], 2: []}, root_id=1)
        # B must come before A
        self.assertEqual(order.index("B"), 0)
        self.assertEqual(order.index("A"), 1)

    def test_multiple_dependencies(self):
        """A → B and A → C → execution order: [B, C, A] or [C, B, A]."""
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        c = _MockFactor(3, "C")
        order = self._sort([a, b, c], {1: [2, 3], 2: [], 3: []}, root_id=1)
        self.assertIn("B", order)
        self.assertIn("C", order)
        # Both B and C must appear before A
        self.assertLess(order.index("B"), order.index("A"))
        self.assertLess(order.index("C"), order.index("A"))

    def test_three_level_dependencies(self):
        """A → B → C → execution order: [C, B, A]."""
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        c = _MockFactor(3, "C")
        order = self._sort([a, b, c], {1: [2], 2: [3], 3: []}, root_id=1)
        self.assertEqual(order, ["C", "B", "A"])

    def test_diamond_dependency(self):
        """
        A → B, A → C, B → D, C → D (diamond).
        D must precede B and C; B and C must precede A.
        """
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        c = _MockFactor(3, "C")
        d = _MockFactor(4, "D")
        order = self._sort(
            [a, b, c, d],
            {1: [2, 3], 2: [4], 3: [4], 4: []},
            root_id=1,
        )
        self.assertLess(order.index("D"), order.index("B"))
        self.assertLess(order.index("D"), order.index("C"))
        self.assertLess(order.index("B"), order.index("A"))
        self.assertLess(order.index("C"), order.index("A"))

    def test_root_appears_last(self):
        """Root factor is always last in execution order."""
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        c = _MockFactor(3, "C")
        order = self._sort([a, b, c], {1: [2], 2: [3], 3: []}, root_id=1)
        self.assertEqual(order[-1], "A")


# ===========================================================================
# 3. Cycle detection
# ===========================================================================

class TestCycleDetection(unittest.TestCase):

    def _sort(self, factors, edges, root_id):
        svc = _make_service_with_mocked_factory()
        nodes = {f.id: f for f in factors}
        return svc._topological_sort(nodes, edges, root_id)

    def test_self_cycle_raises(self):
        """A → A (self-cycle)."""
        a = _MockFactor(1, "A")
        with self.assertRaises(FactorDependencyCycleError) as ctx:
            self._sort([a], {1: [1]}, root_id=1)
        self.assertIn("A", ctx.exception.cycle_path)

    def test_two_factor_cycle_raises(self):
        """A → B, B → A."""
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        with self.assertRaises(FactorDependencyCycleError) as ctx:
            self._sort([a, b], {1: [2], 2: [1]}, root_id=1)
        path = ctx.exception.cycle_path
        # The cycle path must mention both factors
        self.assertIn("A", path)
        self.assertIn("B", path)

    def test_two_factor_cycle_path_contains_back_edge(self):
        """The cycle path must end with the first repeated node."""
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        with self.assertRaises(FactorDependencyCycleError) as ctx:
            self._sort([a, b], {1: [2], 2: [1]}, root_id=1)
        names = ctx.exception.cycle_names
        # First and last element of cycle_names are the same
        self.assertEqual(names[0], names[-1])

    def test_three_factor_cycle_raises(self):
        """A → B → C → A."""
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        c = _MockFactor(3, "C")
        with self.assertRaises(FactorDependencyCycleError) as ctx:
            self._sort([a, b, c], {1: [2], 2: [3], 3: [1]}, root_id=1)
        path = ctx.exception.cycle_path
        self.assertIn("A", path)
        self.assertIn("B", path)
        self.assertIn("C", path)

    def test_three_factor_cycle_names_closed(self):
        """cycle_names[0] == cycle_names[-1] for any cycle."""
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        c = _MockFactor(3, "C")
        with self.assertRaises(FactorDependencyCycleError) as ctx:
            self._sort([a, b, c], {1: [2], 2: [3], 3: [1]}, root_id=1)
        names = ctx.exception.cycle_names
        self.assertEqual(names[0], names[-1])

    def test_cycle_embedded_in_larger_graph(self):
        """
        A → B, A → C, B → D, C → D, D → E, E → B.
        Cycle: B → D → E → B.
        """
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        c = _MockFactor(3, "C")
        d = _MockFactor(4, "D")
        e = _MockFactor(5, "E")
        with self.assertRaises(FactorDependencyCycleError) as ctx:
            self._sort(
                [a, b, c, d, e],
                {1: [2, 3], 2: [4], 3: [4], 4: [5], 5: [2]},
                root_id=1,
            )
        names = ctx.exception.cycle_names
        # The cycle is B→D→E→B (or an equivalent rotation)
        self.assertEqual(names[0], names[-1])
        # All three nodes of the cycle must appear
        inner_names = set(names[:-1])
        self.assertTrue(inner_names <= {"B", "D", "E"})

    def test_cycle_ids_present(self):
        """FactorDependencyCycleError.cycle_ids must be non-empty."""
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        with self.assertRaises(FactorDependencyCycleError) as ctx:
            self._sort([a, b], {1: [2], 2: [1]}, root_id=1)
        self.assertGreater(len(ctx.exception.cycle_ids), 0)

    def test_no_cycle_does_not_raise(self):
        """A valid DAG must not raise even when node ordering is unusual."""
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        c = _MockFactor(3, "C")
        # A→C, A→B, B→C  (C is a shared leaf)
        try:
            self._sort([a, b, c], {1: [3, 2], 2: [3], 3: []}, root_id=1)
        except FactorDependencyCycleError:
            self.fail("FactorDependencyCycleError raised on acyclic graph")


# ===========================================================================
# 4. Dependency graph construction (_build_dependency_graph)
# ===========================================================================

class TestDependencyGraphBuilding(unittest.TestCase):

    def _build(self, root, stored_deps_by_factor, factors_by_id):
        svc = _make_service_with_mocked_factory(
            stored_deps_by_factor=stored_deps_by_factor,
            factors_by_id=factors_by_id,
        )
        return svc._build_dependency_graph(root)

    def test_no_stored_deps(self):
        """Factor with no deps → single-node graph."""
        a = _MockFactor(1, "A")
        nodes, edges, deps_map = self._build(
            root=a,
            stored_deps_by_factor={1: []},
            factors_by_id={},
        )
        self.assertIn(1, nodes)
        self.assertEqual(edges[1], [])

    def test_one_stored_dep(self):
        """A depends on B (stored dep) → graph has edge A→B."""
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        dep = _MockDep(dependent_factor_id=1, independent_factor_id=2)
        nodes, edges, deps_map = self._build(
            root=a,
            stored_deps_by_factor={1: [dep], 2: []},
            factors_by_id={2: b},
        )
        self.assertIn(1, nodes)
        self.assertIn(2, nodes)
        self.assertIn(2, edges[1])

    def test_three_level_stored_deps(self):
        """A→B→C (stored deps) → all three nodes in graph."""
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        c = _MockFactor(3, "C")
        nodes, edges, _ = self._build(
            root=a,
            stored_deps_by_factor={
                1: [_MockDep(1, 2)],
                2: [_MockDep(2, 3)],
                3: [],
            },
            factors_by_id={2: b, 3: c},
        )
        self.assertIn(1, nodes)
        self.assertIn(2, nodes)
        self.assertIn(3, nodes)
        self.assertIn(2, edges[1])
        self.assertIn(3, edges[2])

    def test_dynamic_dep_factors_included_in_graph(self):
        """A factor with calculate_dependencies should add dep to graph."""
        a = _MockFactorWithDynDeps(1, "A", dep_names=["B"])
        b = _MockFactor(2, "B")

        svc = _make_service_with_mocked_factory(
            stored_deps_by_factor={1: [], 2: []},
            factors_by_id={},
            factors_by_name={"B": b},
        )
        nodes, edges, _ = svc._build_dependency_graph(a)

        self.assertIn(2, nodes)
        self.assertIn(2, edges.get(1, []))

    def test_duplicate_edges_not_added(self):
        """If a dep appears in both stored and dynamic, it appears once."""
        b = _MockFactor(2, "B")
        a = _MockFactorWithDynDeps(1, "A", dep_names=["B"])

        svc = _make_service_with_mocked_factory(
            stored_deps_by_factor={
                1: [_MockDep(1, 2)],  # B also as stored dep
                2: [],
            },
            factors_by_id={2: b},
            factors_by_name={"B": b},
        )
        nodes, edges, _ = svc._build_dependency_graph(a)
        # edge from A to B should appear only once
        self.assertEqual(edges[1].count(2), 1)


# ===========================================================================
# 5. Date-set computation
# ===========================================================================

class TestDateSetComputation(unittest.TestCase):

    def _svc(self):
        return _make_service_with_mocked_factory()

    def test_root_gets_target_dates(self):
        svc = self._svc()
        target = [datetime(2024, 1, 10)]
        # Execution order [B, A], root=A (id=1)
        factor_dates = svc._compute_factor_date_sets(
            execution_order=[2, 1],
            target_dates=target,
            stored_deps_map={1: [], 2: []},
        )
        self.assertIn(datetime(2024, 1, 10), factor_dates[1])

    def test_lag_propagated_to_dependency(self):
        svc = self._svc()
        # A (id=1) depends on B (id=2) with lag=1d
        dep = _MockDep(dependent_factor_id=1, independent_factor_id=2, lag=timedelta(days=1))
        target = [datetime(2024, 1, 10)]
        factor_dates = svc._compute_factor_date_sets(
            execution_order=[2, 1],
            target_dates=target,
            stored_deps_map={1: [dep], 2: []},
        )
        # B should be needed at 2024-01-09 (Jan 10 - 1 day)
        self.assertIn(datetime(2024, 1, 9), factor_dates[2])

    def test_no_lag_same_date(self):
        svc = self._svc()
        dep = _MockDep(dependent_factor_id=1, independent_factor_id=2, lag=timedelta(0))
        target = [datetime(2024, 1, 10)]
        factor_dates = svc._compute_factor_date_sets(
            execution_order=[2, 1],
            target_dates=target,
            stored_deps_map={1: [dep], 2: []},
        )
        self.assertIn(datetime(2024, 1, 10), factor_dates[2])

    def test_weekend_skip_in_lag(self):
        svc = self._svc()
        # 2024-01-08 is a Monday; 1 day lag → 2024-01-07 = Sunday → skip to Friday 2024-01-05
        dep = _MockDep(dependent_factor_id=1, independent_factor_id=2, lag=timedelta(days=1))
        target = [datetime(2024, 1, 8)]  # Monday
        factor_dates = svc._compute_factor_date_sets(
            execution_order=[2, 1],
            target_dates=target,
            stored_deps_map={1: [dep], 2: []},
        )
        # Mon - 1d = Sun → back-skip to Friday
        self.assertIn(datetime(2024, 1, 5), factor_dates[2])


# ===========================================================================
# 6. Batch execution ordering
# ===========================================================================

class TestBatchExecutionOrder(unittest.TestCase):
    """
    Verify that dependency factors are resolved for ALL entities before
    any dependent factor is resolved.
    """

    def _make_svc_with_a_depends_b(self):
        """A (id=1) depends on B (id=2) via stored dep."""
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        dep = _MockDep(dependent_factor_id=1, independent_factor_id=2)
        svc = _make_service_with_mocked_factory(
            stored_deps_by_factor={1: [dep], 2: []},
            factors_by_id={2: b},
        )
        return svc, a, b

    def test_execution_order_b_before_a(self):
        svc, a, b = self._make_svc_with_a_depends_b()

        resolve_log = []

        def track_resolve(factor_entity, entity, time_date, repository_type, **kw):
            resolve_log.append(factor_entity.id)
            return _MockFactorValue(factor_entity.id, entity.id, time_date)

        svc._resolver.resolve_factor_value.side_effect = track_resolve

        entities = [_MockEntity(i) for i in range(1, 4)]
        dates = [datetime(2024, 1, 10)]
        svc.resolve_batch(a, entities, dates)

        # All B resolutions must precede any A resolution
        b_indices = [i for i, fid in enumerate(resolve_log) if fid == 2]
        a_indices = [i for i, fid in enumerate(resolve_log) if fid == 1]
        self.assertTrue(b_indices, "B was never resolved")
        self.assertTrue(a_indices, "A was never resolved")
        self.assertLess(max(b_indices), min(a_indices))

    def test_b_resolved_for_all_entities_before_a_starts(self):
        """
        For entities [e1, e2, e3], the resolution log must be:
        [B/e1, B/e2, B/e3, A/e1, A/e2, A/e3]
        """
        svc, a, b = self._make_svc_with_a_depends_b()

        resolve_log = []

        def track_resolve(factor_entity, entity, time_date, repository_type, **kw):
            resolve_log.append((factor_entity.id, entity.id))
            return _MockFactorValue(factor_entity.id, entity.id, time_date)

        svc._resolver.resolve_factor_value.side_effect = track_resolve

        entities = [_MockEntity(i) for i in range(1, 4)]
        dates = [datetime(2024, 1, 10)]
        svc.resolve_batch(a, entities, dates)

        b_entries = [(fid, eid) for fid, eid in resolve_log if fid == 2]
        a_entries = [(fid, eid) for fid, eid in resolve_log if fid == 1]
        b_entity_ids = [eid for _, eid in b_entries]
        a_entity_ids = [eid for _, eid in a_entries]

        # All 3 entities resolved for B first
        self.assertEqual(sorted(b_entity_ids), [1, 2, 3])
        self.assertEqual(sorted(a_entity_ids), [1, 2, 3])

        # The last B call index < first A call index
        b_call_indices = [i for i, (fid, _) in enumerate(resolve_log) if fid == 2]
        a_call_indices = [i for i, (fid, _) in enumerate(resolve_log) if fid == 1]
        self.assertLess(max(b_call_indices), min(a_call_indices))

    def test_result_contains_correct_execution_order(self):
        svc, a, b = self._make_svc_with_a_depends_b()
        svc._resolver.resolve_factor_value.return_value = MagicMock()

        result = svc.resolve_batch(a, [_MockEntity(1)], [datetime(2024, 1, 10)])

        self.assertIsInstance(result, BatchResolutionResult)
        order_names = [f.name for f in result.execution_order]
        self.assertEqual(order_names.index("B"), 0)
        self.assertEqual(order_names.index("A"), 1)

    def test_cycle_in_resolve_batch_raises(self):
        """resolve_batch must propagate FactorDependencyCycleError for cyclic graphs."""
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        # A depends on B, B depends on A
        svc = _make_service_with_mocked_factory(
            stored_deps_by_factor={
                1: [_MockDep(1, 2)],
                2: [_MockDep(2, 1)],
            },
            factors_by_id={1: a, 2: b},
        )
        with self.assertRaises(FactorDependencyCycleError):
            svc.resolve_batch(a, [_MockEntity(1)], [datetime(2024, 1, 10)])


# ===========================================================================
# 7. Shared dependency — resolved only once
# ===========================================================================

class TestSharedDependencyDeduplication(unittest.TestCase):
    """
    Diamond graph: A→B, A→C, B→D, C→D.
    D must appear exactly once in execution_order and be called once per
    (entity, date) pair.
    """

    def _make_diamond_svc(self):
        a = _MockFactor(1, "A")
        b = _MockFactor(2, "B")
        c = _MockFactor(3, "C")
        d = _MockFactor(4, "D")
        svc = _make_service_with_mocked_factory(
            stored_deps_by_factor={
                1: [_MockDep(1, 2), _MockDep(1, 3)],
                2: [_MockDep(2, 4)],
                3: [_MockDep(3, 4)],
                4: [],
            },
            factors_by_id={2: b, 3: c, 4: d},
        )
        return svc, a, b, c, d

    def test_d_appears_once_in_execution_order(self):
        svc, a, *_ = self._make_diamond_svc()
        svc._resolver.resolve_factor_value.return_value = MagicMock()
        result = svc.resolve_batch(a, [_MockEntity(1)], [datetime(2024, 1, 10)])
        d_count = sum(1 for f in result.execution_order if f.id == 4)
        self.assertEqual(d_count, 1)

    def test_d_resolved_once_per_entity_date(self):
        """resolve_factor_value called for D exactly N_entities × N_dates times."""
        svc, a, *_ = self._make_diamond_svc()

        call_log = []

        def track(factor_entity, entity, time_date, repository_type, **kw):
            call_log.append(factor_entity.id)
            return _MockFactorValue(factor_entity.id, entity.id, time_date)

        svc._resolver.resolve_factor_value.side_effect = track

        entities = [_MockEntity(i) for i in range(1, 4)]
        dates = [datetime(2024, 1, 10)]
        svc.resolve_batch(a, entities, dates)

        d_calls = [x for x in call_log if x == 4]
        # 3 entities × 1 date = 3 calls for D
        self.assertEqual(len(d_calls), 3)

    def test_d_before_b_and_c_in_execution_order(self):
        svc, a, b, c, d = self._make_diamond_svc()
        svc._resolver.resolve_factor_value.return_value = MagicMock()
        result = svc.resolve_batch(a, [_MockEntity(1)], [datetime(2024, 1, 10)])
        order_names = [f.name for f in result.execution_order]
        self.assertLess(order_names.index("D"), order_names.index("B"))
        self.assertLess(order_names.index("D"), order_names.index("C"))


# ===========================================================================
# 8. Dynamic dependency cycles
# ===========================================================================

class TestDynamicDependencyCycles(unittest.TestCase):
    """
    Verify that a cycle introduced via calculate_dependencies (dynamic deps)
    is detected at graph-build time and raises FactorDependencyCycleError.
    """

    def test_dynamic_dep_cycle_raises(self):
        """A.calculate_dependencies = ['B'], B.calculate_dependencies = ['A']."""
        a = _MockFactorWithDynDeps(1, "A", dep_names=["B"])
        b = _MockFactorWithDynDeps(2, "B", dep_names=["A"])

        svc = _make_service_with_mocked_factory(
            stored_deps_by_factor={1: [], 2: []},
            factors_by_id={1: a, 2: b},
            factors_by_name={"A": a, "B": b},
        )

        with self.assertRaises(FactorDependencyCycleError) as ctx:
            svc.resolve_batch(a, [_MockEntity(1)], [datetime(2024, 1, 10)])

        path = ctx.exception.cycle_path
        self.assertIn("A", path)
        self.assertIn("B", path)

    def test_dynamic_self_cycle_raises(self):
        """A.calculate_dependencies = ['A'] → self-cycle."""
        a = _MockFactorWithDynDeps(1, "A", dep_names=["A"])

        svc = _make_service_with_mocked_factory(
            stored_deps_by_factor={1: []},
            factors_by_id={1: a},
            factors_by_name={"A": a},
        )

        with self.assertRaises(FactorDependencyCycleError):
            svc.resolve_batch(a, [_MockEntity(1)], [datetime(2024, 1, 10)])

    def test_no_dynamic_dep_no_cycle(self):
        """Factor without calculate_dependencies → no cycle error."""
        a = _MockFactor(1, "A")  # No calculate_dependencies

        svc = _make_service_with_mocked_factory(
            stored_deps_by_factor={1: []},
        )
        svc._resolver.resolve_factor_value.return_value = MagicMock()

        try:
            svc.resolve_batch(a, [_MockEntity(1)], [datetime(2024, 1, 10)])
        except FactorDependencyCycleError:
            self.fail("Unexpected FactorDependencyCycleError for factor with no deps")


# ===========================================================================
# 9. BatchResolutionResult contract
# ===========================================================================

class TestBatchResolutionResult(unittest.TestCase):

    def _make_result(self):
        f = _MockFactor(1, "A")
        return BatchResolutionResult(
            requested_factor=f,
            execution_order=[f],
            resolved_values={1: [MagicMock(), MagicMock()]},
            failed={1: [(2, datetime(2024, 1, 10))]},
        )

    def test_total_resolved_counts_across_factors(self):
        r = self._make_result()
        self.assertEqual(r.total_resolved, 2)

    def test_total_failed_counts_across_factors(self):
        r = self._make_result()
        self.assertEqual(r.total_failed, 1)

    def test_values_for_factor_returns_correct_list(self):
        fv = MagicMock()
        r = BatchResolutionResult(
            requested_factor=_MockFactor(1, "A"),
            execution_order=[],
            resolved_values={42: [fv]},
        )
        self.assertEqual(r.values_for_factor(42), [fv])

    def test_values_for_factor_missing_key_returns_empty(self):
        r = BatchResolutionResult(
            requested_factor=_MockFactor(1, "A"),
            execution_order=[],
        )
        self.assertEqual(r.values_for_factor(999), [])


# ===========================================================================
# 10. resolve_batch end-to-end — no dependency case
# ===========================================================================

class TestResolveBatchNoDeps(unittest.TestCase):

    def test_single_factor_no_deps_resolved(self):
        a = _MockFactor(1, "A")
        svc = _make_service_with_mocked_factory(
            stored_deps_by_factor={1: []},
        )
        mock_fv = _MockFactorValue(1, 10, datetime(2024, 1, 10))
        svc._resolver.resolve_factor_value.return_value = mock_fv

        result = svc.resolve_batch(
            a,
            [_MockEntity(10)],
            [datetime(2024, 1, 10)],
        )

        self.assertEqual(result.total_resolved, 1)
        self.assertEqual(result.total_failed, 0)
        self.assertEqual(result.values_for_factor(1), [mock_fv])

    def test_failed_resolution_counted(self):
        a = _MockFactor(1, "A")
        svc = _make_service_with_mocked_factory(
            stored_deps_by_factor={1: []},
        )
        svc._resolver.resolve_factor_value.return_value = None  # resolver fails

        result = svc.resolve_batch(
            a,
            [_MockEntity(10)],
            [datetime(2024, 1, 10)],
        )

        self.assertEqual(result.total_resolved, 0)
        self.assertEqual(result.total_failed, 1)

    def test_multiple_entities_multiple_dates(self):
        a = _MockFactor(1, "A")
        svc = _make_service_with_mocked_factory(
            stored_deps_by_factor={1: []},
        )
        svc._resolver.resolve_factor_value.side_effect = (
            lambda factor_entity, entity, time_date, repository_type, **kw:
            _MockFactorValue(factor_entity.id, entity.id, time_date)
        )

        entities = [_MockEntity(i) for i in range(1, 6)]
        dates = [datetime(2024, 1, d) for d in range(10, 13)]

        result = svc.resolve_batch(a, entities, dates)

        # 5 entities × 3 dates = 15 resolved values
        self.assertEqual(result.total_resolved, 15)
        self.assertEqual(result.total_failed, 0)


if __name__ == "__main__":
    unittest.main()
