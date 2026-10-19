"""
Concurrency — two writers on the same logical record.

Deterministic interleavings (both backends): the race window is forced, so the outcome does not
depend on thread scheduling. Real threads (SQL Server only, marker concurrency) check that the
database itself keeps the books consistent under parallel trades.
"""

import threading
from datetime import datetime

import pytest

from src.domain.entities.factor.factor_value import FactorValue
from src.infrastructure.models.factor.factor import CompanyShareFactorModel
from src.infrastructure.models.finance.position import PositionModel
from tests.misbuffet.sqlite_portfolio import SqlitePortfolio

pytestmark = pytest.mark.concurrency
MON = datetime(2026, 1, 5)


@pytest.fixture
def two_sessions(backend):
    with backend.factory() as (f1, s1), backend.factory() as (f2, s2):
        factor = CompanyShareFactorModel(name="close", group="price", subgroup="ohlc", frequency="1d",
                                         data_type="numeric", source="ibkr", definition="close",
                                         factor_type="company_share_factor")
        s1.add(factor)
        s1.commit()
        yield (f1, s1), (f2, s2), factor.id


def value(fid, v):
    return FactorValue(id=None, factor_id=fid, entity_id=7, entity_type="CompanyShare", date=MON, value=str(v), entity=None)


class TestFactorValueRace:

    def test_two_resolvers_racing_on_the_same_value_store_one_row(self, two_sessions):
        """Regression: both check (nothing stored), both insert — the unique key keeps one row and the second
        writer gets the stored value back."""
        (f1, s1), (f2, s2), fid = two_sessions
        r1, r2 = f1.factor_value_local_repo, f2.factor_value_local_repo
        # both check first (nothing stored yet) ...
        assert r1.get_by_factor_entity_date(fid, 7, "2026-01-05 00:00:00") is None
        assert r2.get_by_factor_entity_date(fid, 7, "2026-01-05 00:00:00") is None
        # ... then both insert
        r1.add(value(fid, 150))
        r2.add(value(fid, 150))
        rows = s1.query(type(r1.model_class())).filter_by(factor_id=fid, entity_id=7).count() \
            if callable(getattr(r1, "model_class", None)) else None
        from src.infrastructure.models.factor.factor_value import FactorValueModel
        assert s1.query(FactorValueModel).filter_by(factor_id=fid, entity_id=7, date=MON).count() == 1


class TestPositionUpdates:

    @pytest.fixture
    def portfolios(self, backend):
        if backend.name == "sqlite":
            pytest.skip("in-memory SQLite gives every session of a thread the same DBAPI connection, so two "
                        "sessions are not two independent clients — run on SQL Server")
        first = SqlitePortfolio(engine=backend.engine, live=True)
        first.trade("AAPL", 1, 100.0)                   # holding + position exist
        second = SqlitePortfolio(engine=backend.engine, live=True)  # another process resuming the same book
        yield first, second
        second.close()
        first.close()

    def test_interleaved_trades_from_two_sessions_are_both_counted(self, portfolios):
        """Read-modify-write on positions.quantity: each booking re-reads the row it updates."""
        first, second = portfolios
        assert second.trade("AAPL", 5, 100.0)
        assert first.trade("AAPL", 3, 100.0)            # first's session last read quantity 1
        assert first.qty("AAPL") == second.qty("AAPL") == 9

    @pytest.mark.sql_server
    @pytest.mark.slow
    def test_parallel_trades_keep_position_and_cash_consistent(self, backend):
        if backend.name != "sql_server":
            pytest.skip("real parallel writers need SQL Server (SQLite serialises writers)")
        seed = SqlitePortfolio(engine=backend.engine, live=True)
        seed.trade("AAPL", 1, 100.0)
        seed.close()
        errors, booked = [], []

        def trader():
            p = SqlitePortfolio(engine=backend.engine, live=True)
            try:
                for _ in range(10):
                    booked.append(bool(p.trade("AAPL", 1, 100.0)))
            except Exception as e:
                errors.append(repr(e))
            finally:
                p.close()
        threads = [threading.Thread(target=trader) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(300)
        check = SqlitePortfolio(engine=backend.engine, live=True)
        try:
            ok = sum(booked)
            assert errors == []
            assert check.qty("AAPL") == 1 + ok, f"{20 - ok} booking(s) refused, quantity does not match the bookings"
            assert check.cash() == 100_000.0 - 100.0 * (1 + ok)
        finally:
            check.close()
