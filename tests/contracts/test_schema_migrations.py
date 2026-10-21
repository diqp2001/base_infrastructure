"""
Schema migrations of an EXISTING database (BaseFactory._migrate_schema), from the old schema:
  - positions.quantity INTEGER -> DECIMAL(18, 4)        (cash keeps cents)
  - factor_values.value_numeric added and backfilled   (numeric copy of the string value)

SQLite always; SQL Server on a scratch database `base_infra_migration_test` (created and dropped here) — never on
the application database. The SQL Server variant needs a reachable server (marker sql_server).
"""

import re

import pytest
from sqlalchemy import create_engine, text

from src.infrastructure.database.base_factory import BaseFactory

OLD_SQLITE = [
    "CREATE TABLE factor_values (id INTEGER PRIMARY KEY, factor_id INTEGER NOT NULL, entity_id INTEGER NOT NULL, "
    "entity_type VARCHAR(100) NOT NULL, date DATETIME NOT NULL, value VARCHAR(255) NOT NULL, currency_id INTEGER)",
    "CREATE TABLE positions (id INTEGER PRIMARY KEY, portfolio_id INTEGER NOT NULL, quantity INTEGER NOT NULL, "
    "position_type VARCHAR(10) NOT NULL)",
]
OLD_MSSQL = [
    "CREATE TABLE factor_values (id INT IDENTITY PRIMARY KEY, factor_id INT NOT NULL, entity_id INT NOT NULL, "
    "entity_type VARCHAR(100) NOT NULL, date DATETIMEOFFSET NOT NULL, value VARCHAR(255) NOT NULL, currency_id INT NULL)",
    "CREATE TABLE positions (id INT IDENTITY PRIMARY KEY, portfolio_id INT NOT NULL, quantity INT NOT NULL, "
    "position_type VARCHAR(10) NOT NULL)",
]
ROWS = [("1.5", 1.5), ("98497", 98497.0), ("abc", None), ("nan", None), ("-0.25", -0.25)]


def migrate(engine):
    factory = BaseFactory.__new__(BaseFactory)
    factory.engine = engine
    factory._migrate_schema()


def seed(engine):
    with engine.begin() as conn:
        for i, (value, _) in enumerate(ROWS):
            conn.execute(text("INSERT INTO factor_values (factor_id, entity_id, entity_type, date, value) "
                              "VALUES (1, :e, 'CompanyShare', '2026-01-02', :v)"), {"e": i, "v": value})
        conn.execute(text("INSERT INTO positions (portfolio_id, quantity, position_type) VALUES (1, 100000, 'LONG')"))


def check(engine):
    with engine.connect() as conn:
        got = dict(conn.execute(text("SELECT value, value_numeric FROM factor_values")).all())
        assert got == {v: n for v, n in ROWS}
    with engine.begin() as conn:                                          # cents survive a round trip
        conn.execute(text("UPDATE positions SET quantity = 98497.45"))
        assert float(conn.execute(text("SELECT quantity FROM positions")).scalar()) == 98497.45
    migrate(engine)                                                       # idempotent: a second run changes nothing
    with engine.connect() as conn:
        assert dict(conn.execute(text("SELECT value, value_numeric FROM factor_values")).all()) == got


def test_migration_on_sqlite():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        for ddl in OLD_SQLITE:
            conn.execute(text(ddl))
    seed(engine)
    migrate(engine)
    check(engine)


@pytest.mark.sql_server
@pytest.mark.integration
def test_migration_on_sql_server():
    pyodbc = pytest.importorskip("pyodbc")
    from src.infrastructure.database.settings import _sql_server_connection_string
    name = "base_infra_migration_test"
    base = _sql_server_connection_string()
    from urllib.parse import unquote_plus
    plain = re.sub(r"(?i)driver=([^;]+)", lambda m: "driver={" + unquote_plus(m.group(1)).strip("{}") + "}", base)
    master = re.sub(r"(?i)database=[^;]*", "Database=master", plain)
    try:
        admin = pyodbc.connect(master, autocommit=True, timeout=10)
    except pyodbc.Error as e:
        pytest.skip(f"SQL Server not reachable: {e}")
    admin.execute(f"IF DB_ID(N'{name}') IS NOT NULL DROP DATABASE [{name}]")
    admin.execute(f"CREATE DATABASE [{name}]")
    try:
        from sqlalchemy.engine import URL
        engine = create_engine(URL.create("mssql+pyodbc", query={
            "odbc_connect": re.sub(r"(?i)database=[^;]*", f"Database={name}", base)}))
        with engine.connect() as conn:
            assert conn.execute(text("SELECT DB_NAME()")).scalar() == name
        with engine.begin() as conn:
            for ddl in OLD_MSSQL:
                conn.execute(text(ddl))
        seed(engine)
        migrate(engine)
        with engine.connect() as conn:
            kind = conn.execute(text("SELECT DATA_TYPE, NUMERIC_PRECISION, NUMERIC_SCALE FROM INFORMATION_SCHEMA.COLUMNS "
                                     "WHERE TABLE_NAME = 'positions' AND COLUMN_NAME = 'quantity'")).one()
        assert (kind[0], kind[1], kind[2]) == ("decimal", 18, 4)
        check(engine)
        engine.dispose()
    finally:
        admin.execute(f"ALTER DATABASE [{name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
        admin.execute(f"DROP DATABASE [{name}]")
        admin.close()
