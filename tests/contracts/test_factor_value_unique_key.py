"""
factor_values natural key on an EXISTING database (created before the unique constraint): the explicit
clean-up (src/infrastructure/database/factor_value_dedup.py) and the startup migration
(BaseFactory._migrate_schema -> ensure_unique_key).

The legacy table is created with raw DDL (no constraint), as an old database has it.
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from src.infrastructure.database import factor_value_dedup as dedup

MON, TUE = datetime(2026, 1, 5), datetime(2026, 1, 6)


@pytest.fixture
def legacy():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE factor_values (id INTEGER PRIMARY KEY AUTOINCREMENT, factor_id INTEGER NOT NULL,"
                          " entity_id INTEGER NOT NULL, entity_type VARCHAR(100) NOT NULL, date DATETIME NOT NULL,"
                          " value VARCHAR(255) NOT NULL, currency_id INTEGER)"))
    yield engine
    engine.dispose()


def insert(engine, rows):
    with engine.begin() as conn:
        for factor_id, entity_id, entity_type, date, value in rows:
            conn.execute(text("INSERT INTO factor_values (factor_id, entity_id, entity_type, date, value) "
                              "VALUES (:f, :e, :t, :d, :v)"),
                         dict(f=factor_id, e=entity_id, t=entity_type, d=date, v=value))


def table(engine):
    with engine.connect() as conn:
        return sorted(tuple(r) for r in conn.execute(text(
            "SELECT id, factor_id, entity_id, entity_type, value FROM factor_values")).fetchall())


DUPLICATED = [(1, 7, "CompanyShare", MON, "100"), (1, 7, "CompanyShare", MON, "101"),     # same key twice
              (1, 7, "CompanyShare", MON, "102"),                                         # ... three times
              (1, 7, "CompanySharePortfolio", MON, "5"),                                  # other entity type
              (1, 7, "CompanyShare", TUE, "103"), (2, 7, "CompanyShare", MON, "9")]      # other date / factor


class TestCleanUp:

    def test_duplicates_are_reported(self, legacy):
        insert(legacy, DUPLICATED)
        report = dedup.find_duplicates(legacy)
        assert (report.duplicate_keys, report.rows_to_delete) == (1, 2)
        assert report.examples[0][-1] == 3

    def test_dry_run_deletes_nothing(self, legacy):
        insert(legacy, DUPLICATED)
        before = table(legacy)
        report = dedup.deduplicate(legacy, apply=False)
        assert table(legacy) == before and report.deleted == 0 and not report.index_created

    def test_apply_keeps_the_most_recent_row_and_creates_the_index(self, legacy):
        insert(legacy, DUPLICATED)
        report = dedup.deduplicate(legacy, apply=True)
        assert (report.deleted, report.index_created) == (2, True)
        kept = [v for _, f, e, t, v in table(legacy) if (f, e, t) == (1, 7, "CompanyShare")]
        assert len(table(legacy)) == 4 and sorted(kept) == ["102", "103"]      # MON keeps the latest (102)
        assert dedup.has_unique_key(legacy)
        with pytest.raises(IntegrityError):
            insert(legacy, [(1, 7, "CompanyShare", MON, "104")])

    def test_apply_twice_is_harmless(self, legacy):
        insert(legacy, DUPLICATED)
        dedup.deduplicate(legacy, apply=True)
        again = dedup.deduplicate(legacy, apply=True)
        assert (again.deleted, again.index_created, again.index_existed) == (0, False, True)


class TestStartupMigration:

    def test_clean_database_gets_the_index(self, legacy):
        insert(legacy, [r for r in DUPLICATED if r[4] not in ("101", "102")])
        report = dedup.ensure_unique_key(legacy)
        assert report.index_created and dedup.has_unique_key(legacy)

    def test_database_with_duplicates_is_left_untouched(self, legacy):
        insert(legacy, DUPLICATED)
        before = table(legacy)
        report = dedup.ensure_unique_key(legacy)
        assert not report.index_created and report.rows_to_delete == 2
        assert table(legacy) == before and not dedup.has_unique_key(legacy)

    def test_existing_index_is_detected(self, legacy):
        dedup.ensure_unique_key(legacy)
        assert dedup.ensure_unique_key(legacy).index_existed

    def test_new_databases_get_the_constraint_from_the_model(self):
        from src.infrastructure.models import ModelBase
        engine = create_engine("sqlite:///:memory:")
        ModelBase.metadata.create_all(engine)
        try:
            assert dedup.has_unique_key(engine)
        finally:
            engine.dispose()

    def test_cli_dry_run(self, legacy, monkeypatch, capsys):
        insert(legacy, DUPLICATED)
        monkeypatch.setattr("sqlalchemy.create_engine", lambda url: legacy)
        assert dedup.main(["--db", "sqlite"]) == 0
        out = capsys.readouterr().out
        assert "2 row(s) to delete" in out and "dry run" in out
        assert len(table(legacy)) == len(DUPLICATED)
