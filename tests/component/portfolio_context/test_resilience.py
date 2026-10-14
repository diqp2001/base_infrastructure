"""
Resilience: database failures while booking a trade, IBKR connection loss and retries.

Rules verified:
- a trade is booked atomically (order, fill, position, cash): a failure anywhere stores nothing,
  execute_trade returns False and the order is never re-submitted;
- the session is usable again after a failure;
- connection retries are bounded (1 + IBKR_CONNECT_RETRIES) and spaced by the configured delay;
- a disconnected broker refuses orders, and the reconciliation blocks trading.
"""

import logging
from unittest.mock import Mock, patch

import pytest

from tests.misbuffet.sqlite_portfolio import SqlitePortfolio

logging.getLogger("sqlite_portfolio").setLevel(logging.CRITICAL)


@pytest.fixture
def p():
    portfolio = SqlitePortfolio()
    portfolio.container("AAPL")                         # structure exists: only the booking is under test
    portfolio.tm._resolve_account_id(None)
    yield portfolio
    portfolio.close()


def books(p):
    return dict(qty=p.qty("AAPL"), cash=p.cash(), orders=len(p.orders()), txns=len(p.transactions()))


EMPTY = dict(qty=0, cash=100_000.0, orders=0, txns=0)


class TestAtomicBooking:

    def test_booking_a_trade_is_one_commit(self, p):
        p.trade("AAPL", 1, 150.0)                       # first trade also creates the holding (pre-submit)
        with patch.object(p.session, "commit", wraps=p.session.commit) as commit:
            assert p.trade("AAPL", 9, 150.0)
        assert commit.call_count == 1
        assert books(p) == dict(qty=10, cash=98_500.0, orders=4, txns=4)

    def test_failing_final_commit_stores_nothing(self, p):
        with patch.object(p.session, "commit", side_effect=RuntimeError("database unavailable")):
            assert p.trade("AAPL", 10, 150.0) is False
        p.session.rollback()
        assert books(p) == EMPTY

    @pytest.mark.parametrize("step", ["_record_fill", "_update_position", "_update_cash_for_trade"])
    def test_failure_in_any_step_rolls_the_whole_booking_back(self, p, step):
        original = getattr(p.tm, step)

        def failing(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError(f"{step} lost the connection")
        with patch.object(p.tm, step, side_effect=failing):
            assert p.trade("AAPL", 10, 150.0) is False
        assert books(p) == EMPTY

    @pytest.mark.parametrize("step", ["_record_fill", "_update_position", "_update_cash_for_trade"])
    def test_a_step_that_swallows_its_error_still_aborts_the_booking(self, p, step):
        """Regression: steps log and swallow errors; the booking used to continue (cash without position)."""
        session = p.session
        real_flush = session.flush
        target = {"_record_fill": "transactions", "_update_position": "positions",
                  "_update_cash_for_trade": "positions"}[step]
        calls = {"n": 0}

        def flush(*args, **kwargs):
            dirty = {type(o).__tablename__ for o in list(session.new) + list(session.dirty)}
            if target in dirty and step == "_update_cash_for_trade":
                calls["n"] += 1
                if calls["n"] < 2:                 # the asset position update passes, the cash one fails
                    return real_flush(*args, **kwargs)
            if target in dirty:
                raise RuntimeError("deadlock victim")
            return real_flush(*args, **kwargs)
        with patch.object(session, "flush", side_effect=flush):
            result = p.trade("AAPL", 10, 150.0)
        session.rollback()
        assert result is False
        assert books(p) == EMPTY

    def test_order_is_never_resubmitted_after_a_booking_failure(self, p):
        p.trade("AAPL", 1, 150.0)
        with patch.object(p.session, "commit", side_effect=RuntimeError("database unavailable")):
            assert p.trade("AAPL", 10, 150.0) is False
        assert p.market_order.call_count == 2           # one per trade, never a retry

    def test_the_next_trade_works_after_a_failure(self, p):
        with patch.object(p.session, "commit", side_effect=RuntimeError("database unavailable")):
            p.trade("AAPL", 10, 150.0)
        p.session.rollback()
        assert p.trade("AAPL", 10, 150.0)
        assert books(p) == dict(qty=10, cash=98_500.0, orders=2, txns=2)


class TestIBKRConnection:

    def make(self, retries, delay="0"):
        from src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker
        with patch.dict("os.environ", {"IBKR_CONNECT_RETRIES": str(retries), "IBKR_CONNECT_RETRY_DELAY": delay}):
            broker = InteractiveBrokersBroker({"host": "127.0.0.1", "port": 1, "client_id": 1})
        return broker

    @pytest.mark.parametrize("retries", [0, 2, 5])
    def test_connection_attempts_are_bounded(self, retries):
        broker = self.make(retries)
        attempts = []
        with patch.dict("os.environ", {"IBKR_CONNECT_RETRIES": str(retries), "IBKR_CONNECT_RETRY_DELAY": "7"}), \
                patch("src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker.IBTWSClient") as client, \
                patch("src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker.time.sleep") as sleep:
            client.return_value.connect_to_tws.side_effect = lambda: attempts.append(1) or False
            assert broker._connect_impl() is False
        assert len(attempts) == 1 + retries
        assert [c.args[0] for c in sleep.call_args_list] == [7.0] * retries

    def test_success_on_a_retry_stops_retrying(self):
        broker = self.make(5)
        results = iter([False, False, True])
        with patch.dict("os.environ", {"IBKR_CONNECT_RETRIES": "5", "IBKR_CONNECT_RETRY_DELAY": "0"}), \
                patch("src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker.IBTWSClient") as client, \
                patch("src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker.time.sleep"), \
                patch.object(broker, "_update_account_info"), patch.object(broker, "_start_monitoring"):
            client.return_value.connect_to_tws.side_effect = lambda: next(results)
            assert broker._connect_impl() is True
        assert client.return_value.connect_to_tws.call_count == 3

    def test_disconnected_broker_refuses_orders(self):
        from src.application.services.misbuffet.common import Symbol
        from src.application.services.misbuffet.common.orders import MarketOrder
        broker = self.make(0)
        broker.ib_connection = Mock(is_connected=Mock(return_value=False))
        assert broker._place_order_impl(MarketOrder(symbol=Symbol.create_equity("SPY"), quantity=1)) is False
        broker.ib_connection.place_order.assert_not_called()

    def test_lost_connection_blocks_reconciled_trading(self):
        from src.application.services.misbuffet.algorithm.position_reconciler import IBKRSnapshotProvider, PositionReconciler
        ib = Mock(is_connected=Mock(return_value=False))
        rec = PositionReconciler(lambda t: 0, lambda: [], IBKRSnapshotProvider(ib))
        result = rec.check()
        assert result.ok is False and "unavailable" in result.error


class TestRestart:

    def test_live_restart_resumes_the_book(self):
        from tests.persistence import Backend
        backend = Backend("sqlite")
        first = SqlitePortfolio(engine=backend.engine, live=True)
        first.trade("AAPL", 10, 150.0)
        first.close()
        restarted = SqlitePortfolio(engine=backend.engine, live=True)
        try:
            assert restarted.portfolio.id == first.portfolio.id
            assert (restarted.qty("AAPL"), restarted.cash()) == (10, 98_500.0)
            assert len(restarted.orders()) == 2
        finally:
            restarted.close()
            backend.dispose()

    def test_backtest_rerun_starts_from_a_clean_book(self):
        from tests.persistence import Backend
        backend = Backend("sqlite")
        first = SqlitePortfolio(engine=backend.engine)
        first.trade("AAPL", 10, 150.0)
        first.close()
        rerun = SqlitePortfolio(engine=backend.engine)
        try:
            assert rerun.portfolio.id == first.portfolio.id
            assert (rerun.qty("AAPL"), rerun.cash(), len(rerun.orders())) == (0, 100_000.0, 0)
        finally:
            rerun.close()
            backend.dispose()

    def test_backtest_reset_keeps_factor_values_of_other_entities_with_the_same_id(self):
        """Regression: the reset deleted factor_values by entity_id only — e.g. the close history of the
        share whose id equals the portfolio id."""
        from tests.persistence import Backend
        backend = Backend("sqlite")
        first = SqlitePortfolio(engine=backend.engine)
        pid = first.portfolio.id
        from src.infrastructure.models.factor.factor import CompanyShareFactorModel
        from src.infrastructure.models.factor.factor_value import FactorValueModel
        from datetime import datetime
        factor = CompanyShareFactorModel(name="close", group="price", subgroup="ohlc", frequency="1d", data_type="numeric",
                                         source="ibkr", definition="close", factor_type="company_share_factor")
        first.session.add(factor)
        first.session.commit()
        first.session.add_all([
            FactorValueModel(factor_id=factor.id, entity_id=pid, entity_type="CompanyShare", date=datetime(2026, 1, 2), value="150"),
            FactorValueModel(factor_id=factor.id, entity_id=pid, entity_type="PortfolioModel", date=datetime(2026, 1, 2), value="1"),
        ])
        first.session.commit()
        first.close()
        rerun = SqlitePortfolio(engine=backend.engine)
        try:
            left = {(r.entity_type, r.value) for r in rerun.session.query(FactorValueModel).filter_by(entity_id=pid)}
            assert ("CompanyShare", "150") in left
            assert ("PortfolioModel", "1") not in left
        finally:
            rerun.close()
            backend.dispose()

