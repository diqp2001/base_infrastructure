"""
P.03 — broker_orders / broker_executions on SQLite and on the SQL Server test database (`backend` fixture):
the live order path end to end (intent -> submitted -> statuses -> executions -> commission) and the uniqueness the
idempotency relies on.
"""

from datetime import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from src.application.services.misbuffet.algorithm.order_ledger import OrderLedger
from src.domain.entities.finance.order.broker_order import Execution, SubmissionState
from src.infrastructure.models.finance.order.broker_order import BrokerExecutionModel, BrokerOrderModel
from tests.misbuffet.sqlite_portfolio import SqlitePortfolio

NOW = datetime(2026, 10, 28, 15, 0)


@pytest.fixture
def book(backend):
    b = SqlitePortfolio(engine=backend.engine, shares=("AAPL",))
    b.ledger = OrderLedger(b.factory, clock=lambda: NOW)
    engine_order = SimpleNamespace(submission_outcome="sent", broker_order_id=8801, broker_client_id=3)
    b.tm.attach_ledger(b.ledger, submission_probe=lambda: b.probe)
    b.probe = None

    def submit(ticker, qty, tag=""):
        b.probe = engine_order
        return SimpleNamespace(order_id="QC1")
    b.submit = submit
    yield b
    b.session.rollback()
    ids = [o.id for o in b.orders()]
    b.session.query(BrokerExecutionModel).filter(BrokerExecutionModel.exec_id.like("contract-%")).delete(
        synchronize_session=False)
    if ids:
        b.session.query(BrokerOrderModel).filter(BrokerOrderModel.order_id.in_(ids)).delete(synchronize_session=False)
    b.session.commit()
    b.close()


def test_the_live_path_round_trips_through_the_database(book):
    assert book.trade("AAPL", 10, 100.0, submit=book.submit) is True
    bo = book.ledger.orders.get_all()[-1]
    assert (bo.submission_state, bo.broker_order_id, bo.client_id) == (SubmissionState.SUBMITTED, 8801, 3)
    book.ledger.enqueue({"kind": "status", "order_id": 8801, "client_id": 3, "status": "Submitted", "filled": 4,
                         "remaining": 6, "avg_fill_price": 100.0, "perm_id": 123456789})
    for i, qty in enumerate((4, 6, 6)):                                  # the last one replays the second
        book.ledger.enqueue({"kind": "execution", "exec_id": f"contract-{min(i, 1)}", "order_id": 8801,
                             "perm_id": 123456789, "shares": qty, "price": 100.0, "side": "BOT",
                             "time": "20261028  10:00:00"})
    book.ledger.enqueue({"kind": "commission", "exec_id": "contract-1", "commission": 1.0, "currency": "USD"})
    book.ledger.drain()
    assert book.ledger.anomalies == [] and book.ledger.duplicates == 1
    assert (book.qty("AAPL"), book.cash()) == (10, pytest.approx(100_000.0 - 1_000.0 - 1.0))
    bo = book.ledger.orders.get_by_perm_id("IBKR", 123456789)
    assert (bo.status, bo.filled_quantity, bo.remaining_quantity) == ("PARTIALLY_FILLED", 4, 6)
    assert [e.booked for e in book.ledger.executions.get_by_order_id(bo.order_id)] == [True, True]


def test_an_exec_id_is_stored_once(book):
    book.trade("AAPL", 1, 100.0, submit=book.submit)
    repo = book.ledger.executions
    repo.add(Execution("contract-dup", "IBKR", "AAPL", "BUY", 1, 100.0, NOW))
    with pytest.raises(IntegrityError):
        repo.add(Execution("contract-dup", "IBKR", "AAPL", "BUY", 1, 100.0, NOW))


def test_discrepancies_are_stored_open_then_resolved(backend):
    from src.domain.entities.finance.order.discrepancy import Discrepancy, DiscrepancyKind
    from src.infrastructure.models.finance.order.broker_order import TradingDiscrepancyModel
    from src.infrastructure.repositories.local_repo.finance.order.broker_order_repository import DiscrepancyRepository
    session = backend.session()
    repo = DiscrepancyRepository(session)
    try:
        d = repo.add(Discrepancy(DiscrepancyKind.POSITION_MISMATCH, "contract-AAPL", "strategy 1, broker 2", NOW, True))
        assert repo.get_open_by_key(DiscrepancyKind.POSITION_MISMATCH, "contract-AAPL").id == d.id
        d.resolve("matched", NOW)
        repo.update(d)
        assert repo.get_open_by_key(DiscrepancyKind.POSITION_MISMATCH, "contract-AAPL") is None
        latest = repo.get_latest_by_key(DiscrepancyKind.POSITION_MISMATCH, "contract-AAPL")
        assert (latest.resolution, latest.blocking, latest.is_open) == ("matched", True, False)
    finally:
        session.rollback()
        session.query(TradingDiscrepancyModel).filter(TradingDiscrepancyModel.key.like("contract-%")).delete(
            synchronize_session=False)
        session.commit()
        session.close()


def test_trading_controls_are_appended_and_read_back(backend):
    from src.application.services.misbuffet.brokers.trading_controls import TradingControlsService
    from src.domain.entities.finance.order.trading_control import ControlMode, ControlScope
    from src.infrastructure.models.finance.order.trading_control import TradingControlModel
    from src.infrastructure.repositories.local_repo.finance.order.broker_order_repository import (
        TradingControlRepository,
    )
    session = backend.session()
    svc = TradingControlsService(TradingControlRepository(session), clock=lambda: NOW)
    try:
        svc.set(ControlScope.STRATEGY, "contract-strategy", ControlMode.REDUCE_ONLY, "contract test", "pytest")
        mode, reasons = svc.mode_for(None, "contract-strategy")
        assert mode is ControlMode.REDUCE_ONLY and "contract test" in reasons[0]
    finally:
        session.rollback()
        session.query(TradingControlModel).filter(TradingControlModel.target == "contract-strategy").delete(
            synchronize_session=False)
        session.commit()
        session.close()


def test_an_order_points_to_the_decision_that_sent_it(book):
    """P.06.05: trading_decisions + broker_orders.decision_id, on SQLite and on the SQL Server test database."""
    from src.domain.entities.finance.order.trading_decision import TradingDecision
    from src.infrastructure.models.finance.order.trading_decision import TradingDecisionModel
    decisions = book.factory.trading_decision_local_repo
    d = decisions.add(TradingDecision(strategy="CONTRACT_TEST", account="DU1", bar=datetime(2026, 10, 28, 14, 50),
                                      decided_at=NOW, targets={"AAPL": 0.25, "MSFT": -0.1}, artifact_id=38,
                                      note="contract"))
    try:
        book.ledger.current_decision_id = d.id
        assert book.trade("AAPL", 10, 100.0, submit=book.submit) is True
        book.ledger.current_decision_id = None
        bo = book.ledger.orders.get_all()[-1]
        assert bo.decision_id == d.id
        stored = decisions.get_by_id(d.id)
        assert (stored.strategy, stored.targets, stored.artifact_id) == ("CONTRACT_TEST",
                                                                          {"AAPL": 0.25, "MSFT": -0.1}, 38)
        assert decisions.get_recent("CONTRACT_TEST")[0].id == d.id
        with pytest.raises(NotImplementedError):
            decisions.update(stored)                                  # append-only
    finally:
        book.session.rollback()
        book.session.query(TradingDecisionModel).filter(TradingDecisionModel.strategy == "CONTRACT_TEST").delete(
            synchronize_session=False)
        book.session.commit()
