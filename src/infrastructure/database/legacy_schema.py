"""
Pre-Alembic reconciliation — brings a database created BEFORE the Alembic baseline (revision 0001) to that baseline,
so it can then be stamped (``alembic stamp head``). Run explicitly, never at application start-up.

These are the additive changes BaseFactory used to apply at every start-up until 2026-11-23 (each approved when it
was introduced), plus one index the start-up ALTER never created:
  - factor_values.currency_id added; factor_values.value_numeric added and backfilled from value;
  - the factor_values natural unique key (only when no duplicates: factor_value_dedup);
  - positions.quantity INTEGER -> DECIMAL(18, 4) (SQL Server);
  - broker_orders.decision_id added, and its index ix_broker_orders_decision_id (declared by the model);
  - factor_value_provenance.selection added.
The strategy / universe migration (it rebuilds tables) is only reported: strategy_universe_migration --apply.

    python -m src.infrastructure.database.legacy_schema            # the application database (settings)
    python -m src.infrastructure.database.legacy_schema --url sqlite:///C:/tmp/old.db

Back up first (SQL Server: a COPY_ONLY backup) and run it on the *_test copy before the application database. It
never drops anything. Afterwards: ``python -m src.infrastructure.database.migration_status`` must report no
difference before ``alembic stamp head``.
"""

from __future__ import annotations

import argparse

from sqlalchemy import inspect, text


def reconcile(engine, log=print) -> None:
    """Apply the pre-Alembic additive upgrades the database lacks (idempotent: a second run changes nothing)."""
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        sqlite = engine.dialect.name == 'sqlite'

        if 'factor_values' in existing_tables:
            existing_cols = {c['name'] for c in inspector.get_columns('factor_values')}
            if 'currency_id' not in existing_cols:
                sql = ("ALTER TABLE factor_values ADD COLUMN currency_id INTEGER" if sqlite
                       else "ALTER TABLE factor_values ADD currency_id INTEGER NULL")
                with engine.begin() as conn:
                    conn.execute(text(sql))
                log("Migrated: added currency_id to factor_values")

            # unique (factor_id, entity_id, entity_type, date): created only when no duplicates exist
            from src.infrastructure.database.factor_value_dedup import ensure_unique_key
            report = ensure_unique_key(engine)
            if report.index_created:
                log("Migrated: unique index on factor_values (factor_id, entity_id, entity_type, date)")
            elif not report.index_existed:
                log(f"Schema migration warning: {report.summary()}\n  -> run "
                    f"'python -m src.infrastructure.database.factor_value_dedup' (dry run, then --apply)")
            if 'value_numeric' not in existing_cols:
                _add_value_numeric(engine, log)
        if 'positions' in existing_tables:
            quantity = next((c for c in inspector.get_columns('positions') if c['name'] == 'quantity'), None)
            if quantity is not None and not sqlite and 'INT' in str(quantity['type']).upper():
                with engine.begin() as conn:                     # cash keeps cents
                    conn.execute(text("ALTER TABLE positions ALTER COLUMN quantity DECIMAL(18, 4) NOT NULL"))
                log("Migrated: positions.quantity INTEGER -> DECIMAL(18, 4)")
        if 'broker_orders' in existing_tables:
            order_cols = {c['name'] for c in inspector.get_columns('broker_orders')}
            if 'decision_id' not in order_cols:                  # P.06.05
                sql = ("ALTER TABLE broker_orders ADD COLUMN decision_id INTEGER" if sqlite
                       else "ALTER TABLE broker_orders ADD decision_id INTEGER NULL")
                with engine.begin() as conn:
                    conn.execute(text(sql))
                log("Migrated: added decision_id to broker_orders")
            indexes = {i['name'] for i in inspect(engine).get_indexes('broker_orders')}
            if 'ix_broker_orders_decision_id' not in indexes:   # declared by the model (index=True)
                with engine.begin() as conn:
                    conn.execute(text("CREATE INDEX ix_broker_orders_decision_id ON broker_orders (decision_id)"))
                log("Migrated: index ix_broker_orders_decision_id")
        if 'factor_value_provenance' in existing_tables:
            provenance_cols = {c['name'] for c in inspector.get_columns('factor_value_provenance')}
            if 'selection' not in provenance_cols:              # BI-026 column on a BI-025 table
                sql = ("ALTER TABLE factor_value_provenance ADD COLUMN selection VARCHAR(255)" if sqlite
                       else "ALTER TABLE factor_value_provenance ADD selection VARCHAR(255) NULL")
                with engine.begin() as conn:
                    conn.execute(text(sql))
                log("Migrated: added selection to factor_value_provenance")
        # Strategy / Universe domain (2026-11-19): rebuilds tables, so it is never applied here - only reported
        from src.infrastructure.database.strategy_universe_migration import plan
        pending = plan(engine)
        if pending.pending:
            log(f"Schema migration warning: {pending.summary()}\n  -> back up, then run "
                f"'python -m src.infrastructure.database.strategy_universe_migration --apply'")
    except Exception as e:
        log(f"Schema migration warning: {e}")


def _add_value_numeric(engine, log=print) -> None:
    """Add factor_values.value_numeric and backfill it from the string value (unparsable -> NULL)."""
    sqlite = engine.dialect.name == 'sqlite'
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE factor_values ADD COLUMN value_numeric FLOAT" if sqlite
                          else "ALTER TABLE factor_values ADD value_numeric FLOAT NULL"))
    with engine.begin() as conn:
        if sqlite:
            conn.execute(text("UPDATE factor_values SET value_numeric = CAST(value AS REAL) "
                              "WHERE trim(value) GLOB '*[0-9]*' AND CAST(value AS REAL) || '' <> ''"))
        else:
            conn.execute(text("UPDATE factor_values SET value_numeric = TRY_CAST(value AS FLOAT) "
                              "WHERE value_numeric IS NULL"))
    log("Migrated: added factor_values.value_numeric (backfilled from value)")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Bring a pre-Alembic database to the Alembic baseline (additive only)")
    p.add_argument("--url", help="SQLAlchemy URL (default: the application's SQL Server settings)")
    a = p.parse_args(argv)
    from sqlalchemy import create_engine
    from src.infrastructure.database.settings import get_database_url
    engine = create_engine(a.url or get_database_url("sql_server"))
    with engine.connect() as conn:
        name = conn.exec_driver_sql("SELECT DB_NAME()").scalar() if engine.dialect.name == "mssql" else a.url
    print(f"reconciling {name} ...")
    reconcile(engine)
    from src.infrastructure.database.migration_status import status
    s = status(engine, compare=True)
    print(f"schema vs models: {len(s.differences)} difference(s)")
    for d in s.differences:
        print(f"  - {d}")
    return 0 if not s.differences else 1


if __name__ == "__main__":
    raise SystemExit(main())
