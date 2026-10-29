"""P.06.02–P.06.04: the live order path (ledger, discrepancies, controls) visible in the read-only dashboard."""

import datetime as dt
import tempfile

from sqlalchemy import insert

from src.application.services.monitoring.db_monitor import DatabaseMonitor
from src.application.services.monitoring.service import MonitoringService, trading_alerts
from src.application.services.monitoring.status import ERROR, HEALTHY, UNKNOWN
from src.infrastructure.models import ModelBase
from src.infrastructure.repositories.local_repo.monitoring.monitoring_read_repository import guard_read_only
from tests.monitoring.helpers import build_service, fed_ibkr_monitor, make_config, sqlite_engine

NOW = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def service(rows=True, resolved=False):
    engine = sqlite_engine()
    names = ("orders", "broker_orders", "broker_executions", "trading_discrepancies", "trading_controls")
    ModelBase.metadata.create_all(engine, tables=[ModelBase.metadata.tables[n] for n in names])
    t = ModelBase.metadata.tables
    if rows:
        with engine.begin() as conn:                     # setup writes before the read-only guard
            conn.execute(insert(t["broker_orders"]).values(
                order_id=1, broker="IBKR", symbol="F", side="BUY", requested_quantity=1, submission_state="submitted",
                status="FILLED", filled_quantity=1, broker_order_id=8, created_at=NOW))
            conn.execute(insert(t["broker_orders"]).values(
                order_id=2, broker="IBKR", symbol="F", side="SELL", requested_quantity=1, submission_state="unknown",
                status="PENDING", filled_quantity=0, created_at=NOW - dt.timedelta(hours=1)))
            conn.execute(insert(t["broker_executions"]).values(
                exec_id="E1", broker="IBKR", order_id=1, symbol="F", side="BUY", quantity=1, price=12.19,
                executed_at=NOW, commission=0.12, commission_booked=True, booked=True))
            conn.execute(insert(t["broker_executions"]).values(
                exec_id="X1", broker="IBKR", symbol="F", side="BUY", quantity=1, price=12.1, executed_at=NOW,
                booked=False, commission_booked=False, notes="no internal order"))
            conn.execute(insert(t["trading_discrepancies"]).values(
                kind="external_execution", key="X1", broker="IBKR", detail="BUY 1 F", blocking=True, detected_at=NOW,
                resolved_at=NOW if resolved else None, resolution="manual test trade" if resolved else None))
            for i, mode in enumerate(("disabled", "enabled")):
                conn.execute(insert(t["trading_controls"]).values(
                    scope="global", target="*", mode=mode, reason=f"r{i}", changed_by="owner",
                    changed_at=NOW + dt.timedelta(minutes=i)))
    db = DatabaseMonitor(engine=guard_read_only(engine), db_level_read_only=None)
    return MonitoringService(make_config(tempfile.mkdtemp()), db=db, ibkr=fed_ibkr_monitor())


def test_the_trading_view_shows_orders_executions_discrepancies_and_controls():
    svc = service()
    svc.collect_data()
    view = svc.trading()
    d = view["data"]
    assert view["status"] == ERROR                                     # blocking discrepancy + UNKNOWN order
    assert [o["order_id"] for o in d["open_orders"]] == [2]
    assert {e["exec_id"] for e in d["executions"]} == {"E1", "X1"} and d["unbooked_executions"] == 1
    assert [c["mode"] for c in d["controls"]] == ["enabled"]           # the latest row per scope is in force
    kinds = sorted((a["severity"], a["kind"]) for a in d["alerts"])
    assert ("critical", "discrepancy") in kinds and ("critical", "order") in kinds
    assert ("warning", "execution") in kinds and ("warning", "order") in kinds    # stuck for an hour
    overview = svc.overview()
    assert overview["status"] == ERROR and overview["data"]["trading"]["summary"]["alerts"] == len(d["alerts"])


def test_an_empty_order_path_is_healthy_and_an_old_database_is_unknown():
    svc = service(rows=False)
    svc.collect_data()
    assert svc.trading()["status"] == HEALTHY
    old = build_service(tempfile.mkdtemp())                            # no P.03 tables
    old.collect_data()
    assert old.trading()["status"] == UNKNOWN and "before P.03" in old.trading()["error"]


def test_alert_rules():
    now = dt.datetime(2026, 10, 29, 15, 0, tzinfo=dt.timezone.utc)
    alerts = trading_alerts({"controls": [{"scope": "strategy", "target": "CSM", "mode": "reduce_only", "reason": "x",
                                           "changed_by": "o"}], "open_discrepancies": [], "open_orders": [],
                             "unbooked_executions": 0}, now)
    assert [(a["severity"], a["kind"]) for a in alerts] == [("warning", "control")]
    assert trading_alerts({}, now) == []


def test_the_route_and_page_are_read_only():
    from src.interfaces.flask.monitoring_app import create_monitoring_app
    svc = service()
    svc.collect_data()
    client = create_monitoring_app(service_provider=lambda: svc).test_client()
    response = client.get("/monitor/api/trading/status")
    assert response.status_code == 200 and response.get_json()["data"]["unbooked_executions"] == 1
    assert client.get("/monitor/trading").status_code == 200
    assert client.post("/monitor/api/trading/status").status_code == 405



def test_an_owner_resolved_external_execution_no_longer_raises_an_alert():
    svc = service(resolved=True)
    svc.collect_data()
    d = svc.trading()["data"]
    assert d["unbooked_executions"] == 0 and d["open_discrepancies"] == []
    assert [r["resolution"] for r in d["resolved_discrepancies"]] == ["manual test trade"]
