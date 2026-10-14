"""
Factor context — FactorValueResolutionService on a real (in-memory SQLite) store.

Complements tests/test_factor_value_batch_resolution.py (ordering, multi-level graphs, shared
dependencies, cycles, batching, de-duplication) with the cases that need real persistence:
scope isolation (entity, entity type, timestamp), persisted identifiers, reuse vs recompute,
missing observations / definitions / repositories, calculation and repository failures.

Chain under test:  raw close (CompanyShareFactor, IBKR bar stamped at its start)
                   -> CompanyShareMidPriceFactor -> CompanyShareValueFactor
"""

import contextlib
import io
import logging
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.application.services.data.entities.factor.factor_value_resolution_service import FactorValueResolutionService
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import (
    CompanyShareValueFactor,
)
from tests.misbuffet.sqlite_portfolio import T0, SqlitePortfolio

FRIDAY, MONDAY, TUESDAY = datetime(2026, 1, 2), datetime(2026, 1, 5), datetime(2026, 1, 6)
logging.getLogger("factor_resolution_test").setLevel(logging.CRITICAL)


class Context:

    def __init__(self):
        self.p = SqlitePortfolio(shares=("AAPL", "MSFT", "NODATA"))
        self.service = FactorValueResolutionService(factory=self.p.factory,
                                                    logger=logging.getLogger("factor_resolution_test"))
        repo = self.p.factory.get_local_repository("CompanyShareValueFactor")
        d = CompanyShareValueFactor()
        self.value_factor = repo._create_or_get(CompanyShareValueFactor, d.name, group=d.group, subgroup=d.subgroup,
                                                data_type=d.data_type, source=d.source, frequency="1d")

    def share(self, ticker):
        return self.p.factory.company_share_local_repo.get_by_symbol(ticker)

    def resolve(self, ticker_or_entity, when=T0, factor=None, **kw):
        entity = self.share(ticker_or_entity) if isinstance(ticker_or_entity, str) else ticker_or_entity
        with contextlib.redirect_stdout(io.StringIO()):
            return self.service.resolve_factor_value(factor or self.value_factor, entity, when, **kw)

    def stored(self, name="company_share_value"):
        return self.p.factor_values(name)


@pytest.fixture
def ctx():
    c = Context()
    c.p.seed_close("AAPL", FRIDAY, 150.0)
    c.p.seed_close("MSFT", FRIDAY, 400.0)
    yield c
    c.p.close()


class TestScopeIsolation:

    def test_each_instrument_gets_its_own_value(self, ctx):
        assert float(ctx.resolve("AAPL").value) == 150.0
        assert float(ctx.resolve("MSFT").value) == 400.0

    def test_persisted_value_carries_factor_entity_type_and_date(self, ctx):
        value = ctx.resolve("AAPL")
        assert (value.factor_id, value.entity_id, value.date) == (ctx.value_factor.id, ctx.share("AAPL").id, T0)
        assert ctx.stored() == [("CompanyShare", ctx.share("AAPL").id, T0, 150.0)]

    def test_values_never_cross_entity_types_with_the_same_id(self, ctx):
        """An entity of another type that shares the share's id must not receive the share's price."""
        aapl = ctx.share("AAPL")

        class Impostor:                                 # same id, different entity type, no related share
            id = aapl.id

        assert ctx.resolve(Impostor()) is None
        assert all(row[0] == "CompanyShare" for row in ctx.stored())

    def test_value_for_one_date_is_not_served_for_another(self, ctx):
        ctx.resolve("AAPL", MONDAY.replace(hour=16))
        ctx.p.seed_close("AAPL", MONDAY, 160.0)          # Monday bar, closed by Tuesday
        assert float(ctx.resolve("AAPL", TUESDAY.replace(hour=16)).value) == 160.0
        assert sorted(r[3] for r in ctx.stored()) == [150.0, 160.0]

    def test_a_bar_that_has_not_closed_is_never_used(self, ctx):
        ctx.p.seed_close("AAPL", MONDAY, 999.0)          # stamped Monday 00:00, still open Monday 16:00
        assert float(ctx.resolve("AAPL", MONDAY.replace(hour=16)).value) == 150.0

    def test_future_observations_do_not_change_a_past_resolution(self, ctx):
        before = float(ctx.resolve("AAPL", MONDAY.replace(hour=16), force_recalculate=True).value)
        ctx.p.seed_close("AAPL", TUESDAY, 1_000.0)
        after = float(ctx.resolve("AAPL", MONDAY.replace(hour=16), force_recalculate=True).value)
        assert before == after == 150.0


class TestReuseAndRecompute:

    def test_second_resolution_reuses_the_stored_value(self, ctx):
        first = ctx.resolve("AAPL")
        second = ctx.resolve("AAPL")
        assert (second.id, float(second.value)) == (first.id, 150.0)
        assert len(ctx.stored()) == 1

    def test_derived_value_is_recomputed_for_a_new_date_not_carried_forward(self, ctx):
        ctx.resolve("AAPL", MONDAY.replace(hour=16))
        ctx.p.seed_close("AAPL", MONDAY, 155.0)
        assert float(ctx.resolve("AAPL", TUESDAY.replace(hour=16)).value) == 155.0

    def test_duplicate_requests_for_the_same_scope_store_one_row(self, ctx):
        for _ in range(3):
            ctx.resolve("MSFT")
        assert len([r for r in ctx.stored() if r[1] == ctx.share("MSFT").id]) == 1


class TestMissingData:

    def test_no_observation_gives_no_value_and_stores_nothing(self, ctx):
        assert ctx.resolve("NODATA") is None
        assert [r for r in ctx.stored() if r[1] == ctx.share("NODATA").id] == []

    def test_only_stale_observations_beyond_the_staleness_limit_give_no_value(self, ctx):
        far_future = FRIDAY + timedelta(days=400)
        assert ctx.resolve("AAPL", far_future) is None

    def test_factor_without_a_stored_definition_is_refused(self, ctx):
        ghost = CompanyShareValueFactor()
        ghost.id = 987_654                               # never persisted
        assert ctx.resolve("AAPL", factor=ghost) is None
        assert ctx.stored() == []

    def test_entity_without_id_is_refused(self, ctx):
        class NoId:
            id = None
        assert ctx.resolve(NoId()) is None


class TestFailures:

    def test_calculation_error_stores_nothing(self, ctx):
        with patch.object(CompanyShareValueFactor, "calculate", side_effect=ArithmeticError("boom")):
            assert ctx.resolve("AAPL") is None
        assert ctx.stored() == []

    def test_calculation_returning_none_stores_nothing(self, ctx):
        with patch.object(CompanyShareValueFactor, "calculate", return_value=None):
            assert ctx.resolve("AAPL") is None
        assert ctx.stored() == []

    def test_dependency_without_a_repository_gives_no_value(self, ctx):
        real = ctx.p.factory.get_local_repository

        def without_mid_price(key):
            return None if key == "CompanyShareMidPriceFactor" else real(key)

        with patch.object(ctx.p.factory, "get_local_repository", side_effect=without_mid_price):
            assert ctx.resolve("AAPL") is None
        assert ctx.stored() == []

    def test_write_failure_returns_no_value_and_the_session_stays_usable(self, ctx):
        repo = ctx.p.factory.factor_value_local_repo
        with patch.object(type(repo), "add", side_effect=RuntimeError("database unavailable")):
            assert ctx.resolve("AAPL") is None
        assert float(ctx.resolve("AAPL").value) == 150.0     # recovers once the store works again
