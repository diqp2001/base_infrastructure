"""
MonitoringReadRepository — read-only SQL queries for the monitoring dashboard.

* Only SELECT statements are built here (SQLAlchemy Core on the existing ORM tables:
  ``factors``, ``factor_values``, ``financial_assets``); nothing goes through the ORM session,
  so no unit-of-work flush can ever write.
* ``guard_read_only(engine)`` installs a ``before_cursor_execute`` hook that rejects any
  statement that is not SELECT / WITH / SET (defence in depth: the dashboard connects with a
  login that only has ``db_datareader`` on SQL Server).
* All queries are bounded (``LIMIT`` / ``TOP``) and grouped in the database.
"""

import time
from typing import Any, Dict, List, Optional

from sqlalchemy import case, create_engine, distinct, event, func, select, text
from sqlalchemy.engine import Engine

from src.infrastructure.models.factor.factor import FactorModel
from src.infrastructure.models.factor.factor_value import FactorValueModel
from src.infrastructure.models.factor.factor_value_provenance import FactorValueProvenanceModel
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel

READ_ONLY_PREFIXES = ("SELECT", "WITH", "SET")


class ReadOnlyViolation(PermissionError):
    """A non read-only SQL statement was about to be executed on a monitoring connection."""


def _first_keyword(statement: str) -> str:
    s = statement.lstrip()
    while s.startswith("--") or s.startswith("/*"):          # skip leading comments
        s = s.split("\n", 1)[1].lstrip() if s.startswith("--") else s.split("*/", 1)[-1].lstrip()
    s = s.lstrip("(").lstrip()
    return s.split(None, 1)[0].upper() if s else ""


def guard_read_only(engine: Engine) -> Engine:
    """Reject every statement that is not a read (SELECT / WITH) or a session SET."""

    @event.listens_for(engine, "before_cursor_execute", retval=False)
    def _reject_writes(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        if _first_keyword(statement) not in READ_ONLY_PREFIXES:
            raise ReadOnlyViolation(f"monitoring connection refused a non read-only statement: "
                                    f"{_first_keyword(statement)}")

    engine.monitoring_read_only_guard = True
    return engine


def has_read_only_guard(engine: Engine) -> bool:
    return bool(getattr(engine, "monitoring_read_only_guard", False))


def create_read_only_engine(url, login_timeout: int = 5) -> Engine:
    kwargs: Dict[str, Any] = {"pool_pre_ping": True, "pool_recycle": 300}
    if str(getattr(url, "drivername", url)).startswith("mssql"):
        kwargs.update(pool_size=2, max_overflow=1, connect_args={"timeout": login_timeout})
    return guard_read_only(create_engine(url, **kwargs))


class MonitoringReadRepository:

    def __init__(self, engine: Engine):
        self.engine = engine
        self.factors = FactorModel.__table__
        self.values = FactorValueModel.__table__
        self.assets = FinancialAssetModel.__table__
        self.provenance = FactorValueProvenanceModel.__table__

    # ------------------------------------------------------------------ health
    def ping(self) -> Dict[str, Any]:
        """Round-trip latency, server identity and whether the login can write."""
        t0 = time.perf_counter()
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1")).scalar()
            latency_ms = (time.perf_counter() - t0) * 1000.0
            info: Dict[str, Any] = {"latency_ms": round(latency_ms, 1), "dialect": self.engine.dialect.name}
            if self.engine.dialect.name == "mssql":
                row = conn.execute(text(
                    "SELECT DB_NAME() AS db, CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(64)) AS version, "
                    "CAST(SERVERPROPERTY('Edition') AS NVARCHAR(128)) AS edition, "
                    "IS_ROLEMEMBER('db_datareader') AS is_reader, IS_ROLEMEMBER('db_datawriter') AS is_writer, "
                    "IS_ROLEMEMBER('db_owner') AS is_owner, IS_SRVROLEMEMBER('sysadmin') AS is_sysadmin, "
                    "HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'INSERT') AS can_insert, "
                    "HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'UPDATE') AS can_update, "
                    "HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'DELETE') AS can_delete, "
                    "(SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE') AS tables"
                )).mappings().one()
                can_write = bool(row["is_writer"] or row["is_owner"] or row["is_sysadmin"]
                                 or row["can_insert"] or row["can_update"] or row["can_delete"])
                info.update(database=row["db"], server_version=row["version"], edition=row["edition"],
                            table_count=int(row["tables"]), login_can_write=can_write)
            else:
                tables = conn.execute(text(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'")).scalar()
                info.update(database=None, server_version=None, edition=None, table_count=int(tables),
                            login_can_write=None)
        return info

    def table_counts(self) -> Dict[str, int]:
        with self.engine.connect() as conn:
            return {
                "factors": int(conn.execute(select(func.count()).select_from(self.factors)).scalar()),
                "factor_values": int(conn.execute(select(func.count()).select_from(self.values)).scalar()),
                "financial_assets": int(conn.execute(select(func.count()).select_from(self.assets)).scalar()),
            }

    # ------------------------------------------------------------------ factors
    def factor_summary(self, limit: int = 200, source: Optional[str] = None,
                       calculated: Optional[bool] = None) -> List[Dict[str, Any]]:
        """One row per factor: value count, entities, first / last observation date."""
        f, v = self.factors, self.values
        q = (select(f.c.id, f.c.name, f.c.group, f.c.subgroup, f.c.frequency, f.c.source, f.c.factor_type,
                    func.count(v.c.id).label("value_count"),
                    func.count(distinct(v.c.entity_id)).label("entity_count"),
                    func.min(v.c.date).label("first_date"),
                    func.max(v.c.date).label("last_date"))
             .select_from(f.outerjoin(v, v.c.factor_id == f.c.id))
             .group_by(f.c.id, f.c.name, f.c.group, f.c.subgroup, f.c.frequency, f.c.source, f.c.factor_type))
        if source is not None:
            q = q.where(f.c.source == source)
        if calculated is True:
            q = q.where(f.c.source == "calculated")
        elif calculated is False:
            q = q.where(f.c.source != "calculated")
        # factors with values first (most recent first), factors without values last
        q = q.order_by(case((func.max(v.c.date).is_(None), 1), else_=0), func.max(v.c.date).desc(),
                       f.c.name).limit(limit)
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(q).mappings()]

    # ------------------------------------------------------------------ market data
    def market_data_freshness(self, limit: int = 300) -> List[Dict[str, Any]]:
        """Latest observation per (raw data factor, entity) — non-calculated factors only."""
        f, v, a = self.factors, self.values, self.assets
        q = (select(f.c.id.label("factor_id"), f.c.name.label("factor"), f.c.frequency, f.c.source,
                    v.c.entity_type, v.c.entity_id, a.c.symbol,
                    func.count(v.c.id).label("value_count"),
                    func.max(v.c.date).label("last_date"))
             .select_from(v.join(f, v.c.factor_id == f.c.id).outerjoin(a, a.c.id == v.c.entity_id))
             .where(f.c.source != "calculated")
             .group_by(f.c.id, f.c.name, f.c.frequency, f.c.source, v.c.entity_type, v.c.entity_id, a.c.symbol)
             .order_by(func.max(v.c.date).asc())          # stalest first
             .limit(limit))
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(q).mappings()]

    def data_quality(self, limit: int = 100) -> Optional[Dict[str, Any]]:
        """Recorded observation quality (BI-025 provenance, BI-034): counts per status and data type, and the
        latest observations that are not VALID with their reason. None when the provenance table does not exist
        (a database created before BI-025)."""
        from sqlalchemy.exc import OperationalError, ProgrammingError
        p, v, f, a = self.provenance, self.values, self.factors, self.assets
        try:                                     # a plain SELECT: the read-only guard refuses catalogue PRAGMAs
            with self.engine.connect() as conn:
                conn.execute(select(p.c.factor_value_id).limit(1)).first()
        except (OperationalError, ProgrammingError):
            return None
        counts = (select(p.c.status, p.c.data_type, func.count().label("count"))
                  .group_by(p.c.status, p.c.data_type).order_by(p.c.status, p.c.data_type))
        problems = (select(f.c.name.label("factor"), v.c.entity_type, v.c.entity_id, a.c.symbol,
                           v.c.date, p.c.status, p.c.data_type, p.c.rejection_reason, p.c.validations,
                           p.c.ingested_at)
                    .select_from(p.join(v, v.c.id == p.c.factor_value_id).join(f, f.c.id == v.c.factor_id)
                                 .outerjoin(a, a.c.id == v.c.entity_id))
                    .where(p.c.status != "valid")
                    .order_by(v.c.date.desc()).limit(limit))
        with self.engine.connect() as conn:
            return {"counts": [dict(r) for r in conn.execute(counts).mappings()],
                    "problems": [dict(r) for r in conn.execute(problems).mappings()]}

    def data_sources(self) -> List[Dict[str, Any]]:
        f = self.factors
        q = (select(f.c.source, func.count(f.c.id).label("factor_count"))
             .group_by(f.c.source).order_by(f.c.source))
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(q).mappings()]
