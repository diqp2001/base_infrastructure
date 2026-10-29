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

The author of every control and resolution is the OS user (STM_OPERATOR overrides it). Controls are append-only.
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


def main(argv=None, factory=None, out=print) -> int:
    parser = argparse.ArgumentParser(prog="ops", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    for name in ("kill", "unkill", "reduce-only", "disable", "enable"):
        sub.add_parser(name).add_argument("reason")
    resolve = sub.add_parser("resolve")
    resolve.add_argument("discrepancy_id", type=int)
    resolve.add_argument("resolution")
    args = parser.parse_args(argv)

    factory = factory or _factory()
    if args.command == "status":
        status(factory, out)
        return 0
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
