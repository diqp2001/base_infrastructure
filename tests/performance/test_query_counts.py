"""
Performance: SQL statements per operation (deterministic, unlike wall-clock thresholds).

Marker `performance` — excluded from the fast suite and CI stages 1-2:
    python -m pytest -m performance -s
The bounds are generous ceilings that catch N+1 regressions (statements growing with the number
of instruments), not tight benchmarks. Timings are printed for information only.
"""

import logging
import time
from contextlib import contextmanager
from datetime import datetime

import pytest
from sqlalchemy import event

from src.application.services.data.entities.factor.factor_value_resolution_service import FactorValueResolutionService
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import (
    CompanyShareValueFactor,
)
from tests.misbuffet.sqlite_portfolio import T0, SqlitePortfolio, slice_at

pytestmark = pytest.mark.performance
logging.getLogger("sqlite_portfolio").setLevel(logging.CRITICAL)
FRIDAY = datetime(2026, 1, 2)


@contextmanager
def count_statements(engine):
    counter = {"n": 0}

    def before(*_args, **_kwargs):
        counter["n"] += 1
    event.listen(engine, "before_cursor_execute", before)
    started = time.perf_counter()
    try:
        yield counter
    finally:
        counter["seconds"] = time.perf_counter() - started
        event.remove(engine, "before_cursor_execute", before)


def universe(n):
    return tuple(f"S{i:03d}" for i in range(n))


def resolution_cost(n):
    p = SqlitePortfolio(shares=universe(n))
    try:
        for t in universe(n):
            p.seed_close(t, FRIDAY, 100.0)
        service = FactorValueResolutionService(factory=p.factory, logger=logging.getLogger("perf"))
        repo = p.factory.get_local_repository("CompanyShareValueFactor")
        d = CompanyShareValueFactor()
        factor = repo._create_or_get(CompanyShareValueFactor, d.name, group=d.group, subgroup=d.subgroup,
                                     data_type=d.data_type, source=d.source, frequency="1d")
        shares = [p.factory.company_share_local_repo.get_by_symbol(t) for t in universe(n)]
        with count_statements(p.engine) as c:
            for share in shares:
                assert service.resolve_factor_value(factor, share, T0) is not None
        return c
    finally:
        p.close()


def test_factor_resolution_statements_grow_linearly():
    small, large = resolution_cost(2), resolution_cost(10)
    per_small, per_large = small["n"] / 2, large["n"] / 10
    print(f"\nresolution: {per_small:.0f} statements/share (2 shares), {per_large:.0f} (10 shares), "
          f"{large['seconds'] / 10 * 1000:.0f} ms/share")
    assert per_large <= per_small * 1.5, "statements per share grow with the universe size (N+1)"
    assert per_large < 400


def test_set_holdings_statements_per_ticker():
    costs = {}
    for n in (2, 8):
        p = SqlitePortfolio(shares=universe(n))
        try:
            for t in universe(n):
                p.seed_close(t, FRIDAY, 100.0)
            p.upm._algorithm.bar_size_setting = "1 day"
            targets = {__import__("src.domain.entities.finance.financial_assets.share.company_share.company_share",
                                  fromlist=["CompanyShare"]).CompanyShare:
                       [{"name": t, "quantity": 5} for t in universe(n)]}
            with count_statements(p.engine) as c:
                result = p.upm.set_holdings(targets, slice_at(T0, **{t: 100.0 for t in universe(n)}))
            assert all(result.values()) and len(result) == n
            costs[n] = c
        finally:
            p.close()
    per2, per8 = costs[2]["n"] / 2, costs[8]["n"] / 8
    print(f"\nset_holdings: {per2:.0f} statements/ticker (2 tickers), {per8:.0f} (8 tickers), "
          f"{costs[8]['seconds'] / 8 * 1000:.0f} ms/ticker")
    assert per8 <= per2 * 2.0, "statements per ticker grow superlinearly with the number of tickers"


def valuation_cost(n):
    """Statements and time to value the whole portfolio tree (n share holdings + cash) once (BI-019)."""
    p = SqlitePortfolio(shares=universe(n))
    try:
        for t in universe(n):
            p.seed_close(t, FRIDAY, 100.0)
            assert p.trade(t, 5, 100.0, when=T0)
        p.upm._algorithm.time = T0
        with count_statements(p.engine) as c:
            value = p.upm.get_portfolio_value(backtest_date=T0)
        assert float(getattr(value, "value", value)) == pytest.approx(100_000.0)
        return c
    finally:
        p.close()


def test_portfolio_aggregation_statements_grow_linearly():
    """BI-019 budget, recorded before any optimisation: statements per holding must not grow with the number of
    holdings (N+1 across the holding -> sub-portfolio -> main layers), with a generous absolute ceiling."""
    small, large = valuation_cost(2), valuation_cost(8)
    per_small, per_large = small["n"] / 2, large["n"] / 8
    print(f"\nportfolio valuation: {small['n']} statements for 2 holdings, {large['n']} for 8 "
          f"({per_large:.0f}/holding), {large['seconds'] * 1000:.0f} ms for 8")
    # baseline 2026-10-21 (SQLite): 256 statements for 2 holdings, 616 for 8 (~60 per holding + ~136), 0.27 s
    assert per_large <= per_small * 1.5, "statements per holding grow with the number of holdings (N+1)"
    assert large["n"] < 1000 and large["seconds"] < 60
