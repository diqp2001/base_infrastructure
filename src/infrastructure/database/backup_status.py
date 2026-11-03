"""
Backup freshness of the books database (P.08.02): the newest scheduled (not COPY_ONLY) full and log backups recorded
by SQL Server in msdb, and the alerts when they are older than the schedule allows (nightly full, hourly log).
SQL Server only; any other database (SQLite in tests) has no backup history and reports None.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import text

FULL_MAX_AGE = timedelta(hours=26)        # nightly at 02:00, with slack
LOG_MAX_AGE = timedelta(hours=2)          # hourly


def last_backups(session) -> Optional[Dict[str, Optional[datetime]]]:
    """{'database', 'full', 'log'} (local server time, naive) for the session's database; None when not SQL Server."""
    if session.get_bind().dialect.name != "mssql":
        return None
    row = session.execute(text(
        "SELECT DB_NAME(), "
        "MAX(CASE WHEN b.type = 'D' THEN b.backup_finish_date END), "
        "MAX(CASE WHEN b.type = 'L' THEN b.backup_finish_date END) "
        "FROM msdb.dbo.backupset b WHERE b.database_name = DB_NAME() AND b.is_copy_only = 0")).fetchone()
    return {"database": row[0], "full": row[1], "log": row[2]}


def backup_alerts(last: Optional[Dict[str, Optional[datetime]]], now: datetime) -> List[str]:
    """Messages for a missing or stale full / log backup (`now` in the same local server time)."""
    if last is None:
        return []
    out = []
    for kind, limit, job in (("full", FULL_MAX_AGE, "nightly"), ("log", LOG_MAX_AGE, "hourly")):
        when = last.get(kind)
        if when is None:
            out.append(f"no {kind} backup of {last['database']} on record ({job} job not running?)")
        elif now - when > limit:
            out.append(f"last {kind} backup of {last['database']} is {(now - when).total_seconds() / 3600:.0f} h old "
                       f"({job} job not running? SQL Server Agent stopped?)")
    return out
