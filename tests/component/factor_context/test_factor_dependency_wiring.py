"""
Every factor's calculate() can be fed by FactorValueResolutionService — static wiring, one test per class.

For each class that defines calculate() (discovered, see factor_catalog.py):
  1. it can be built with its defaults (the service creates definitions from them);
  2. the factory has a local repository for it (needed to store its definition and values);
  3. it declares calculate_dependencies, and every required calculate() parameter is one the
     service fills (`dependencies`, or a declared dependency / entity / target_date by name);
  4. every dependency is resolvable by the service:
     - DependencySpec: a repository for the dependency type (get_all + _create_or_get) and a
       definition built the way _resolve_dependency_spec builds a missing one satisfies the spec;
     - string: a factor repository (factor-class path) or an entity attribute (e.g. Position).

A class that fails any rule is a strict expected failure listing why, so fixing it flips the test.
Classes the service is not meant to feed (no stored inputs: basket options, generic models, ...) are listed
in factor_catalog.NOT_SERVICE_RESOLVABLE with the reason and skipped.
The end-to-end counterpart (values actually delivered) is test_factor_resolution_end_to_end.py.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.domain.entities.factor.dependency_spec import DependencySpec
from src.infrastructure.repositories.repository_factory import RepositoryFactory
from tests.component.factor_context.factor_catalog import (
    ENTITY_ATTRIBUTE_DEPS, NOT_SERVICE_RESOLVABLE, declared_dependencies, dependency_name, factor_classes, instantiate,
    unfed_parameters,
)


@pytest.fixture(scope="module")
def factory():
    with patch.object(RepositoryFactory, "create_ibkr_client", return_value=None):
        yield RepositoryFactory(MagicMock())


def built_like_the_resolver(spec, parent):
    """The definition _resolve_dependency_spec creates when no stored factor matches the spec."""
    created = spec.factor_type()

    def resolve(value, attr):
        return getattr(parent, attr, None) if value is DependencySpec.SELF else value

    source = resolve(spec.source, "source") or (spec.source_in[0] if spec.source_in else None) \
        or getattr(parent, "source", None)
    if source and spec.source_not_in and source in spec.source_not_in:
        source = "ibkr"
    for attr in ("group", "subgroup", "frequency", "data_type"):
        value = resolve(getattr(spec, attr), attr)
        if value is not None:
            setattr(created, attr, value)
    created.source = source
    return created


def problems_of(cls, factory):
    factor = instantiate(cls)
    if factor is None:
        return ["cannot be built with defaults (needs name / group): the service cannot create its definition"]
    problems = []
    if factory.get_local_repository(cls.__name__) is None:
        problems.append("no local repository in RepositoryFactory")
    try:
        deps = declared_dependencies(factor)
    except Exception as e:                                           # a broken property
        return problems + [f"calculate_dependencies raises {e!r}"]
    if not hasattr(factor, "calculate_dependencies"):
        problems.append("no calculate_dependencies: the service cannot know what to resolve")
    names = [dependency_name(d) for d in deps]
    unfed = unfed_parameters(cls, names)
    if unfed:
        problems.append(f"calculate() parameters never provided: {unfed}")
    for dep in deps:
        name = dependency_name(dep)
        repo = factory.get_local_repository(dep if isinstance(dep, str) else dep.dep_name)
        if isinstance(dep, DependencySpec):
            if repo is None or not hasattr(repo, "get_all") or not hasattr(repo, "_create_or_get"):
                problems.append(f"{name}: no repository with get_all / _create_or_get")
                continue
            try:
                created = built_like_the_resolver(dep, factor)
            except TypeError:
                # raw observation types (e.g. CompanyShareFactor "close") are matched against the
                # definitions stored by the data import; the resolver does not build them
                continue
            if not dep.matches_factor(factor, created):
                problems.append(f"{name}: a definition created for the spec does not satisfy it")
        elif repo is not None and hasattr(repo, "get_factor_entity"):
            # _resolve_factor_class_dep builds the dependency from its defaults
            try:
                repo.get_factor_entity()()
            except TypeError:
                problems.append(f"'{name}': string dependency on a type without defaults — the factor-class "
                                f"path cannot build it (declare a DependencySpec to match stored definitions)")
        elif name not in ENTITY_ATTRIBUTE_DEPS:
            problems.append(f"'{name}': no factor repository and not an entity attribute — never resolved")
    return problems


def _cases():
    with patch.object(RepositoryFactory, "create_ibkr_client", return_value=None):
        factory = RepositoryFactory(MagicMock())
        for name, cls in factor_classes():
            if name in NOT_SERVICE_RESOLVABLE:
                marks = [pytest.mark.skip(reason=f"not service-resolvable: {NOT_SERVICE_RESOLVABLE[name]}")]
            else:
                problems = problems_of(cls, factory)
                marks = [pytest.mark.xfail(strict=True, reason="; ".join(problems))] if problems else []
            yield pytest.param(cls, id=name, marks=marks)


def test_catalog_is_not_empty():
    assert len(factor_classes()) > 100


def test_not_service_resolvable_names_are_catalog_classes():
    """The exclusion list names real factor classes (a renamed / removed class must leave the list)."""
    assert sorted(set(NOT_SERVICE_RESOLVABLE) - set(dict(factor_classes()))) == []


@pytest.mark.parametrize("cls", list(_cases()))
def test_resolution_service_can_feed_calculate(cls, factory):
    assert problems_of(cls, factory) == []
