"""P.08.02 backup freshness: stale or missing scheduled backups of the books database become alerts."""

from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.infrastructure.database.backup_status import backup_alerts, last_backups

NOW = datetime(2026, 11, 3, 15, 0)


def last(full_hours=None, log_hours=None):
    return {"database": "base_infra",
            "full": NOW - timedelta(hours=full_hours) if full_hours is not None else None,
            "log": NOW - timedelta(hours=log_hours) if log_hours is not None else None}


def test_fresh_backups_raise_nothing():
    assert backup_alerts(last(full_hours=13, log_hours=0.5), NOW) == []


def test_stale_or_missing_backups_are_alerts():
    alerts = backup_alerts(last(full_hours=30, log_hours=3), NOW)
    assert len(alerts) == 2 and "full backup of base_infra is 30 h old" in alerts[0] and "log" in alerts[1]
    assert backup_alerts(last(), NOW) == ["no full backup of base_infra on record (nightly job not running?)",
                                          "no log backup of base_infra on record (hourly job not running?)"]


def test_no_backup_history_outside_sql_server():
    engine = create_engine("sqlite://")
    with Session(engine) as session:
        assert last_backups(session) is None
    assert backup_alerts(None, NOW) == []
