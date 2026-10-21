"""BI-014: factor definitions are validated — in the domain constructor and for every factor library entry."""

import pytest

from src.domain.entities.factor.factor import Factor


class Plain(Factor):
    pass


@pytest.mark.parametrize("field, bad", [("group", "prices"), ("subgroup", "dailyy"), ("frequency", "1day"),
                                        ("data_type", "float64"), ("source", "bloomberg")])
def test_unknown_values_are_refused(field, bad):
    kwargs = dict(name="x", group="price", subgroup="daily", frequency="1d", data_type="numeric", source="ibkr")
    kwargs[field] = bad
    with pytest.raises(ValueError, match=f"Invalid {field}"):
        Plain(**kwargs)


def test_a_valid_definition_is_accepted():
    f = Plain(name="close", group="price", subgroup="daily", frequency="1d", data_type="numeric", source="ibkr")
    assert (f.group, f.frequency, f.source) == ("price", "1d", "ibkr")


def _entries():
    from src.application.services.data.entities.factor.factor_library.factor_definition_config import FACTOR_LIBRARY

    def walk(library_name, key, config):
        yield f"{library_name}.{key}", config
        deps = config.get("dependencies") or {}
        if isinstance(deps, dict):
            for dep_key, dep in deps.items():
                if isinstance(dep, dict):
                    yield from walk(library_name, f"{key}->{dep_key}", dep)

    for library_name, library in FACTOR_LIBRARY.items():
        for key, config in library.items():
            if isinstance(config, dict):
                yield from walk(library_name, key, config)


ENTRIES = list(_entries())
FIELDS = (("group", Factor.GROUPS), ("subgroup", Factor.SUBGROUPS), ("frequency", Factor.FREQUENCIES),
          ("data_type", Factor.DATA_TYPES), ("source", Factor.SOURCES))


def test_the_library_is_not_empty():
    assert len(ENTRIES) > 50


@pytest.mark.parametrize("field, allowed", FIELDS, ids=[f for f, _ in FIELDS])
def test_every_library_entry_uses_canonical_values(field, allowed):
    bad = {name: cfg[field] for name, cfg in ENTRIES if cfg.get(field) is not None and cfg[field] not in allowed}
    assert bad == {}


def test_raw_ibkr_library_entries_name_their_series():
    """BI-036: a raw IBKR bar field declared in the library has subgroup = its IBKR whatToShow."""
    from src.domain.entities.factor.source_policy import validate_raw_definition
    bad = {}
    for name, cfg in ENTRIES:
        try:
            validate_raw_definition(cfg.get("name"), cfg.get("group"), cfg.get("subgroup"), cfg.get("source"))
        except ValueError as e:
            bad[name] = str(e)
    assert bad == {}
