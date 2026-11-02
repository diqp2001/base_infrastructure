"""
Operator commands for the STM 10m live deployment (RUNBOOK.md). They act on the database only — never on IBKR — so they
work while a session is running in another process: trading controls are read before every order.

    python -m src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.ops status
    ... ops kill "<reason>"                 # GLOBAL disabled: no new order anywhere
    ... ops reduce-only "<reason>"          # this strategy may only reduce positions
    ... ops disable "<reason>"              # this strategy may not trade
    ... ops enable "<reason>"               # this strategy back to normal (a global kill stays in force)
    ... ops unkill "<reason>"               # GLOBAL back to enabled
    ... ops resolve <discrepancy id> "<what was checked / done>"
    ... ops adopt <exec id> "<why>"         # book an external execution into the strategy's book (session STOPPED)

The author of every control and resolution is the OS user (STM_OPERATOR overrides it). Controls are append-only.
`adopt` is the one command that writes to the book: run it only while no session is running.
"""

import argparse
import getpass
import os
import sys
from datetime import datetime, timezone

from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live import config as project_config
from src.application.services.misbuffet.brokers.trading_controls import TradingControlsService
from src.domain.entities.finance.order.trading_control import GLOBAL_TARGET, ControlMode, ControlScope


def _factory():
    from src.application.services.database_service.database_service import DatabaseService
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    db = DatabaseService(project_config.CONFIG_TEST['DB_TYPE'])
    db.set_ext_db()
    return RepositoryFactory(db.session)


def _operator() -> str:
    return os.getenv("STM_OPERATOR") or getpass.getuser()


def status(factory, out=print) -> None:
    live = project_config.LIVE
    controls = TradingControlsService(factory.trading_control_local_repo)
    mode, reasons = controls.mode_for(live['account'], live['strategy'])
    out(f"account {live['account']}  strategy {live['strategy']}  trading: {mode.value.upper()}"
        + (f"  ({'; '.join(reasons)})" if reasons else ""))
    for d in factory.trading_discrepancy_local_repo.get_open():
        out(f"  discrepancy {d.id} {'BLOCKING ' if d.blocking else ''}{d.kind.value} {d.key}: {d.detail}")
    for o in factory.broker_order_local_repo.get_open():
        out(f"  open order {o.order_id} {o.side} {o.requested_quantity:g} {o.symbol} {o.status} "
            f"submission {o.submission_state.value} broker id {o.broker_order_id}")


def _book_portfolios(factory, symbol: str):
    """(portfolio_id, cash_portfolio_id) of the strategy's book: those of its latest order in `symbol`, else of its
    latest order (every broker order of this database's live ledger belongs to the strategy)."""
    orders = sorted((o for o in factory.broker_order_local_repo.get_all() if o.portfolio_id is not None
                     and o.cash_portfolio_id is not None), key=lambda o: o.order_id)
    same = [o for o in orders if o.symbol == symbol]
    last = (same or orders or [None])[-1]
    return (last.portfolio_id, last.cash_portfolio_id) if last else (None, None)


def adopt(factory, exec_id: str, reason: str, portfolio_id=None, cash_portfolio_id=None, out=print) -> int:
    """P.06.15: book an external execution (manual trade in TWS) as a fill of the strategy and resolve its
    external_execution discrepancy; the position check then matches IBKR again."""
    from src.application.services.misbuffet.algorithm.order_ledger import OrderLedger
    from src.application.services.misbuffet.algorithm.trade_manager import TradeManager
    from src.domain.entities.finance.order.discrepancy import DiscrepancyKind
    ledger = OrderLedger(factory, TradeManager(factory))
    ex = ledger.executions.get_by_exec_id(ledger.broker, exec_id)
    if ex is None:
        out(f"execution {exec_id} is not stored")
        return 1
    default_portfolio, default_cash = _book_portfolios(factory, ex.symbol)
    portfolio_id = portfolio_id if portfolio_id is not None else default_portfolio
    cash_portfolio_id = cash_portfolio_id if cash_portfolio_id is not None else default_cash
    if portfolio_id is None or cash_portfolio_id is None:
        out("no strategy order to take the book's portfolios from: pass --portfolio-id and --cash-portfolio-id")
        return 1
    who = f"{reason} ({_operator()})"
    try:
        bo = ledger.adopt(exec_id, portfolio_id, cash_portfolio_id, who)
    except ValueError as e:
        out(str(e))
        return 1
    out(f"execution {exec_id} {ex.side} {ex.quantity:g} {ex.symbol} @ {ex.price} adopted as order {bo.order_id} "
        f"(portfolio {portfolio_id}, cash portfolio {cash_portfolio_id})")
    for message in ledger.anomalies:
        out(f"  warning: {message}")
    repo = factory.trading_discrepancy_local_repo
    d = repo.get_open_by_key(DiscrepancyKind.EXTERNAL_EXECUTION, exec_id)
    if d is not None:
        d.resolve(f"adopted into order {bo.order_id}: {who}", datetime.now(timezone.utc))
        repo.update(d)
        out(f"discrepancy {d.id} resolved")
    out("a position_mismatch on this name resolves itself at the next start once book and IBKR agree")
    return 0


def main(argv=None, factory=None, out=print) -> int:
    parser = argparse.ArgumentParser(prog="ops", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    for name in ("kill", "unkill", "reduce-only", "disable", "enable"):
        sub.add_parser(name).add_argument("reason")
    resolve = sub.add_parser("resolve")
    resolve.add_argument("discrepancy_id", type=int)
    resolve.add_argument("resolution")
    adopt_cmd = sub.add_parser("adopt")
    adopt_cmd.add_argument("exec_id")
    adopt_cmd.add_argument("reason")
    adopt_cmd.add_argument("--portfolio-id", type=int)
    adopt_cmd.add_argument("--cash-portfolio-id", type=int)
    args = parser.parse_args(argv)

    factory = factory or _factory()
    if args.command == "status":
        status(factory, out)
        return 0
    if args.command == "adopt":
        return adopt(factory, args.exec_id, args.reason, args.portfolio_id, args.cash_portfolio_id, out)
    if args.command == "resolve":
        repo = factory.trading_discrepancy_local_repo
        d = repo.get_by_id(args.discrepancy_id)
        if d is None:
            out(f"discrepancy {args.discrepancy_id} does not exist")
            return 1
        d.resolve(f"{args.resolution} ({_operator()})", datetime.now(timezone.utc))
        repo.update(d)
        out(f"discrepancy {d.id} resolved; the running session re-checks IBKR before its next order")
        return 0
    controls = TradingControlsService(factory.trading_control_local_repo)
    strategy = project_config.LIVE['strategy']
    scope, target, mode = {
        "kill": (ControlScope.GLOBAL, GLOBAL_TARGET, ControlMode.DISABLED),
        "unkill": (ControlScope.GLOBAL, GLOBAL_TARGET, ControlMode.ENABLED),
        "reduce-only": (ControlScope.STRATEGY, strategy, ControlMode.REDUCE_ONLY),
        "disable": (ControlScope.STRATEGY, strategy, ControlMode.DISABLED),
        "enable": (ControlScope.STRATEGY, strategy, ControlMode.ENABLED),
    }[args.command]
    controls.set(scope, target, mode, args.reason, _operator())
    out(f"{scope.value} {target}: {mode.value} — applies from the next order")
    status(factory, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
