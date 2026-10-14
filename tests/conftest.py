"""
Root pytest configuration.

1. Markers from location — tests are classified without editing the (unittest-style) files:
     tests/architecture/  -> architecture
     tests/repositories/  -> contract
     tests/integration/   -> integration (+ sql_server / ibkr per test class)
     SQLite-backed suites -> component
     everything else      -> unit
   Select with -m, e.g. the fast suite:  pytest -m "not integration and not ibkr and not sql_server"

2. Safety net for every test that is not explicitly an opted-in IBKR test:
   - ibapi EClient.connect raises (no socket to TWS / IB Gateway is ever opened);
   - RepositoryFactory.create_ibkr_client returns None (it otherwise connects on demand).
   IBKR tests run only with the `ibkr` marker AND IBKR_LIVE_SMOKE=1, and are read-only.
3. `sql_server` tests run only against a dedicated test database (DB_NAME ending in "_test");
   they are skipped otherwise, so they can never write into the application database.
"""

import os

import pytest

# test files / classes that need real infrastructure (file path suffix -> extra markers)
INFRASTRUCTURE = {
    "integration/test_docker_services.py::TestSqlServerConnectivity": ("integration", "sql_server"),
    "integration/test_docker_services.py::TestIbGatewayConnectivity": ("integration", "ibkr"),
    "integration/test_ibkr_live_readonly.py": ("integration", "ibkr"),
    "misbuffet/test_reconciler_lifecycle.py::LiveGatewayReadOnlySmokeTest": ("integration", "ibkr"),
    "test_option_price_factor_deps.py": ("integration", "sql_server"),
}

# suites that run real repositories / services on an in-memory SQLite database
COMPONENT_FILES = (
    "misbuffet/test_trade_manager.py",
    "misbuffet/test_set_holdings_chain.py",
    "misbuffet/test_upm_decisions.py",
    "test_universe_and_ml.py",
    "test_factor_value_batch_resolution.py",
    "monitoring/",
    "spatio_temporal_momentum/test_stm_persistence.py",
    "spatio_temporal_momentum/test_stm_trading_cycle.py",
    "spatio_temporal_momentum/test_stm_lookahead.py",
)

LAYER_MARKERS = {"unit", "component", "contract", "architecture", "integration", "e2e", "performance"}


def _relative(nodeid: str) -> str:
    return nodeid[len("tests/"):] if nodeid.startswith("tests/") else nodeid


def pytest_collection_modifyitems(config, items):
    for item in items:
        rel = _relative(item.nodeid)
        added = set()
        for prefix, markers in INFRASTRUCTURE.items():
            if rel.startswith(prefix):
                added.update(markers)
        if rel.startswith("architecture/"):
            added.add("architecture")
        elif rel.startswith("repositories/"):
            added.add("contract")
        elif rel.startswith("integration/"):
            added.add("integration")
        elif any(rel.startswith(f) for f in COMPONENT_FILES) and "integration" not in added:
            added.add("component")
        existing = {m.name for m in item.iter_markers()}
        if not (LAYER_MARKERS & (existing | added)):
            added.add("unit")
        for name in sorted(added - existing):
            item.add_marker(getattr(pytest.mark, name))


def pytest_runtest_setup(item):
    if item.get_closest_marker("ibkr") is not None and os.getenv("IBKR_LIVE_SMOKE") != "1":
        pytest.skip("ibkr tests read the real Gateway: opt in with IBKR_LIVE_SMOKE=1")
    if item.get_closest_marker("sql_server") is not None:
        database = os.getenv("DB_NAME", "base_infra")
        if not database.endswith("_test"):
            pytest.skip(f"sql_server tests need a dedicated *_test database (DB_NAME={database!r} "
                        f"is the application database)")


def _ibkr_allowed(item) -> bool:
    return item.get_closest_marker("ibkr") is not None and os.getenv("IBKR_LIVE_SMOKE") == "1"


@pytest.fixture(autouse=True)
def _no_unintended_ibkr_connection(request, monkeypatch):
    """Every test except opted-in `ibkr` tests: no IBKR socket, no on-demand IBKR client."""
    if _ibkr_allowed(request.node):
        yield
        return
    from ibapi.client import EClient

    def _refuse(*args, **kwargs):
        raise ConnectionRefusedError("tests never connect to IBKR (mark `ibkr` and set IBKR_LIVE_SMOKE=1)")

    monkeypatch.setattr(EClient, "connect", _refuse)
    try:
        from src.infrastructure.repositories.repository_factory import RepositoryFactory
        monkeypatch.setattr(RepositoryFactory, "create_ibkr_client", lambda self: None)
    except Exception:
        pass
    yield
