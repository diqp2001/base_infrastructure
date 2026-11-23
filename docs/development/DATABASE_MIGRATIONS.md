# Database migrations (Alembic)

The application database schema (SQL Server `base_infra`, or SQLite) is versioned with **Alembic**. Each schema
change is a reviewed migration script, applied with an explicit command. The application never changes the schema
itself.

```
SQLAlchemy models (src/infrastructure/models, one registry: ModelBase)
        -> ModelBase.metadata
        -> Alembic (alembic.ini, src/infrastructure/database/migrations/)
        -> database schema
```

## Layout

| Path | Role |
|---|---|
| `alembic.ini` | Alembic configuration (repo root). It holds no database URL. |
| `src/infrastructure/database/migrations/env.py` | `target_metadata = ModelBase.metadata`, URL resolution, safety filter. |
| `src/infrastructure/database/migrations/versions/` | The migrations. `0001` = the baseline: every table of the models, 2026-11-23. |
| `src/infrastructure/database/migration_status.py` | Read only: a database's revision, the head, and its differences from the models. |
| `src/infrastructure/database/legacy_schema.py` | Brings a database created before Alembic to the baseline (additive only), before stamping. |

The domain and application layers know nothing of Alembic.

## How Alembic gets the models

`env.py` imports `src.infrastructure.models`. That package defines `ModelBase` and imports every application model,
so `ModelBase.metadata` is complete before any comparison.

- **One registry:** there is exactly one application metadata. Importing any other model module adds nothing to it;
  `tests/migrations` checks this.
- **Legacy back-testing models:** bars, ticks, symbols and enums use their own `LegacyBackTestingBase` and are not
  managed.
- **Backtest-tracking database:** `src/infrastructure/backtest/models.py` has its own Base, for a separate SQLite file
  (`backtest_tracking.db`) that is not part of the application schema.

## Which database

There is no URL in `alembic.ini`. `env.py` uses the first of these that is set:

1. `alembic -x url=<SQLAlchemy URL> ...` — e.g. `-x url=sqlite:///C:/tmp/scratch.db`.
2. `DATABASE_URL` (environment variable) — a migration-only override.
3. The application's SQL Server settings (`src/infrastructure/database/settings.py`): `DB_ODBC_CONNECTION_STRING`,
   or `DB_HOST` / `DB_NAME` / `DB_USER` / ... With nothing set, it uses the Windows localhost `base_infra`.

So, by default, `alembic` acts on the same database as the application.

## Commands

```bash
alembic current                                   # the database's revision
alembic history                                   # the migrations
alembic upgrade head                              # apply every pending migration
alembic downgrade -1                              # undo the last one
alembic revision --autogenerate -m "add universe factor"   # draft a migration from the model changes
alembic upgrade head --sql                        # print the SQL instead of running it (offline)
python -m src.infrastructure.database.migration_status       # read only: revision, head, schema vs models
```

Add `-x url=...` to target another database, e.g. `alembic -x url=sqlite:///C:/tmp/scratch.db upgrade head`.

With Docker (the `app` service carries the database settings):

```bash
docker compose run --rm app alembic upgrade head
docker compose run --rm app alembic current
```

Deployment order:
1. Start the database.
2. Run the migrations (explicitly, as above).
3. Start the application.

Migrations never run automatically at start-up. The `trader` service connects with a login that has no DDL rights
and must never migrate.

## Creating a migration

1. Change the models in `src/infrastructure/models`. A new model module must be imported by
   `src/infrastructure/models/__init__.py`, or Alembic will not see it.
2. `alembic revision --autogenerate -m "what changes"` — it compares the models with the database the command points
   at. Use a database at head, e.g. a scratch SQLite: `-x url=sqlite:///C:/tmp/scratch.db` after `upgrade head`.
3. **Review the generated file before applying it.** Autogenerate is a draft:
   - **Destructive operations:** look for every `drop_table`, `drop_column`, `alter_column` (type, nullable to
     non-nullable), primary key change, foreign key change and unique constraint change.
   - **Renames:** autogenerate cannot detect a rename. It writes a drop plus an add, which loses data; rewrite it as
     `op.alter_column(..., new_column_name=...)`.
   - **Data migrations:** backfills and type conversions are written by hand.
   - **Safety filter:** autogenerate never proposes dropping a table that the models do not define, nor its indexes
     (`include_object`). `strategy_configurations`, kept on purpose, is one such table. To drop a table, write it by
     hand.
4. **Test it.** Run `upgrade head`, `downgrade -1` and `upgrade head` again on a scratch SQLite, then on the SQL
   Server test database (`pytest tests/migrations`, and `-m sql_server` with `DB_NAME=base_infra_test`).
5. **Apply to base_infra** only after a COPY_ONLY backup and the owner's approval.

SQLite cannot alter tables in place, so migrations run in batch mode there (`render_as_batch`). Write dialect-neutral
operations; avoid SQLite- or SQL Server-only SQL in migrations unless guarded by `op.get_bind().dialect.name`.

## SQL Server notes

- **Schema:** tables live in the default schema (`dbo`); no schema is named in the migrations.
- **Identity columns:** `Integer` primary keys with `autoincrement` become `INT IDENTITY`.
- **Types:**
  - `String(n)` becomes `VARCHAR(n)`, and `Text` becomes `VARCHAR(max)` on a live SQL Server 2012+, as
    `create_all` made them. The offline `--sql` script, with no server version, prints the legacy `TEXT`;
    generate it from a live connection when the exact DDL matters;
  - `DateTime` becomes `DATETIME`, and `DateTime(timezone=True)` becomes `DATETIMEOFFSET`;
  - `Numeric(p, s)` becomes `DECIMAL(p, s)`;
  - `Boolean` becomes `BIT`;
  - `JSON` becomes `NVARCHAR(max)`.
- **Foreign keys and indexes:** named as in the models. The cycle holdings.position_id <-> positions is added after
  both tables exist, because SQL Server leaves `use_alter` keys out of `CREATE TABLE`.
- **Naming convention:** none is configured on `ModelBase.metadata`. Adding one now would rename the existing
  constraints and indexes of `base_infra` (a migration of renames with no benefit), so the current names are kept.
  New constraints should be given explicit names.
- **Transactions:** SQL Server DDL is transactional, so a failing migration rolls back. SQLite is not transactional
  for DDL.

## Existing databases (adoption)

A database created before Alembic has every table but no `alembic_version` table. Do not run `upgrade head` on it: it
would try to create every table again. Do not delete it either. Adopt it instead:

1. **Back up.** On SQL Server, take a COPY_ONLY backup, and adopt `base_infra_test` (or a restored copy) first.
2. **Compare:** `python -m src.infrastructure.database.migration_status` (read only) lists how the schema differs from
   the models.
3. **Reconcile:** `python -m src.infrastructure.database.legacy_schema` applies the pre-Alembic additive upgrades the
   database lacks: columns and indexes that start-up used to add before 2026-11-23. If the strategy / universe
   migration is reported, run `python -m src.infrastructure.database.strategy_universe_migration --apply`
   (after the backup).
4. **Compare again:** it must report 0 differences.
5. **Stamp:** `alembic stamp head`. This only writes the revision row; no table is created or dropped.
6. From then on: `alembic upgrade head` applies the new migrations.

**Never stamp an outdated database.** Stamping tells Alembic that the schema is already at head. Alembic then skips
the migrations that would have created the missing columns or tables. The database stays broken, and later migrations
fail or corrupt data on top of it. Stamp only after step 4 reports 0 differences.

State on 2026-11-23:
- **`base_infra` (Windows):** adopted at revision `0001` (owner's approval).
  - **Backup:** COPY_ONLY with checksums, verified: `MSSQL\Backup\base_infra_before_alembic_stamp_20261123.bak`.
  - **Reconciliation:** it created one index, `ix_broker_orders_decision_id`. The model declares it; the old start-up
    `ALTER` added the column without it.
  - **Stamp:** done once the comparison reported 0 differences.
- **`base_infra_test`:** adopted at `0001` first (0 differences, nothing to reconcile).
- **Docker `sqlserver`:** not adopted; it still needs the strategy / universe migration before step 4.

## Fresh database

Create the empty database (Docker: the `sqlserver-init` service creates `DB_NAME`), then run `alembic upgrade head`.
Every table of the models is created and the database is stamped at head. The application then starts normally.

`BaseFactory` (application start-up) only reports the status: a warning when the database is not at head, or not under
migration control. It no longer runs `create_all` or `ALTER TABLE`.

`Database.initialize_database_and_create_all_tables()` remains as an explicit bootstrap for scratch / test databases:
`create_all` creates missing tables but never alters existing ones. In-memory test databases still use
`ModelBase.metadata.create_all`.
