"""BI-034: observation quality (BI-025 provenance) visible in the read-only dashboard, without querying tables."""

import datetime as dt
import json
import tempfile

from sqlalchemy import insert

from src.application.services.monitoring.service import MonitoringService
from src.application.services.monitoring.status import DEGRADED, UNKNOWN
from src.application.services.monitoring.db_monitor import DatabaseMonitor
from src.infrastructure.models.factor.factor_value_provenance import FactorValueProvenanceModel
from src.infrastructure.repositories.local_repo.monitoring.monitoring_read_repository import guard_read_only
from tests.monitoring.helpers import build_service, fed_ibkr_monitor, make_config, sqlite_engine


def service_with_provenance():
    engine = sqlite_engine()
    FactorValueProvenanceModel.__table__.create(engine)
    t = FactorValueProvenanceModel.__table__
    with engine.begin() as conn:                                  # setup writes before the read-only guard
        conn.execute(insert(t).values(factor_value_id=1, field="close", source="ibkr", data_type="MIDPOINT",
                                      frequency="1d", status="valid"))
        conn.execute(insert(t).values(factor_value_id=2, field="close", source="ibkr", data_type="TRADES",
                                      frequency="1d", status="rejected", rejection_reason="",
                                      validations=json.dumps([{"rule": "positive_price", "passed": False,
                                                               "reason": "price 0.0 <= 0"}]),
                                      ingested_at=dt.datetime(2026, 10, 20, 21, 0)))
        conn.execute(insert(t).values(factor_value_id=3, field="momentum", source="calculated",
                                      data_type="CALCULATED", frequency="1d", status="stale"))
    db = DatabaseMonitor(engine=guard_read_only(engine), db_level_read_only=None)
    return MonitoringService(make_config(tempfile.mkdtemp()), db=db, ibkr=fed_ibkr_monitor())


def test_counts_and_problems_are_shown():
    svc = service_with_provenance()
    svc.collect_data()
    view = svc.data_quality()
    assert view["status"] == DEGRADED
    counts = {(c["status"], c["data_type"]): c["count"] for c in view["data"]["counts"]}
    assert counts == {("rejected", "TRADES"): 1, ("stale", "CALCULATED"): 1, ("valid", "MIDPOINT"): 1}
    assert view["data"]["not_valid"] == 2
    rejected = next(p for p in view["data"]["problems"] if p["status"] == "rejected")
    assert rejected["symbol"] == "SPY" and "price 0.0 <= 0" in rejected["validations"]


def test_a_database_without_provenance_is_unknown_not_an_error():
    svc = build_service(tempfile.mkdtemp())
    svc.collect_data()
    view = svc.data_quality()
    assert view["status"] == UNKNOWN and "no observation provenance" in view["error"]


def test_the_route_is_read_only():
    from src.interfaces.flask.monitoring_app import create_monitoring_app
    svc = service_with_provenance()
    svc.collect_data()
    client = create_monitoring_app(service_provider=lambda: svc).test_client()
    response = client.get("/monitor/api/data-quality/status")
    assert response.status_code == 200 and response.get_json()["data"]["not_valid"] == 2
    assert client.post("/monitor/api/data-quality/status").status_code == 405
