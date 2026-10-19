"""
factor_values natural key: (factor_id, entity_id, entity_type, date) — one value per key.

New databases get the unique constraint from FactorValueModel (create_all). An existing database gets
the unique index from BaseFactory._migrate_schema, but only when it holds no duplicate rows: removing
duplicates deletes data, so it is never done implicitly. Run it explicitly:

    python -m src.infrastructure.database.factor_value_dedup             # dry run: report only
    python -m src.infrastructure.database.factor_value_dedup --apply     # delete duplicates + create the index
    python -m src.infrastructure.database.factor_value_dedup --db sqlite # another database type

Of each set of rows with the same key the most recent one (highest id, i.e. the last value written)
is kept.
"""

import argparse
from dataclasses import dataclass, field
from typing import List

from sqlalchemy import inspect, text

INDEX_NAME = "uq_factor_values_natural_key"
KEY = "factor_id, entity_id, entity_type, date"


@dataclass
class DedupReport:
    duplicate_keys: int = 0
    rows_to_delete: int = 0
    examples: List[tuple] = field(default_factory=list)   # (factor_id, entity_id, entity_type, date, count)
    deleted: int = 0
    index_created: bool = False
    index_existed: bool = False

    def summary(self) -> str:
        lines = [f"factor_values: {self.duplicate_keys} key(s) stored more than once, "
                 f"{self.rows_to_delete} row(s) to delete (the most recent row of each key is kept)"]
        lines += [f"  factor {f} {t}:{e} at {d}: {n} rows" for f, e, t, d, n in self.examples]
        if self.deleted:
            lines.append(f"deleted {self.deleted} duplicate row(s)")
        if self.index_existed:
            lines.append(f"unique index {INDEX_NAME} already present")
        elif self.index_created:
            lines.append(f"unique index {INDEX_NAME} created")
        return "\n".join(lines)


def has_unique_key(engine) -> bool:
    """Whether factor_values already enforces the natural key (index or constraint)."""
    insp = inspect(engine)
    names = {i.get("name") for i in insp.get_indexes("factor_values")}
    names |= {c.get("name") for c in insp.get_unique_constraints("factor_values")}
    return INDEX_NAME in names


def find_duplicates(engine, limit: int = 20) -> DedupReport:
    report = DedupReport()
    with engine.connect() as conn:
        rows = conn.execute(text(
            f"SELECT {KEY}, COUNT(*) AS n FROM factor_values GROUP BY {KEY} HAVING COUNT(*) > 1")).fetchall()
    report.duplicate_keys = len(rows)
    report.rows_to_delete = sum(int(r[-1]) - 1 for r in rows)
    report.examples = [tuple(r) for r in rows[:limit]]
    return report


def deduplicate(engine, apply: bool = False) -> DedupReport:
    """Report duplicates; with apply=True delete them (keep the highest id per key) and create the index."""
    report = find_duplicates(engine)
    report.index_existed = has_unique_key(engine)
    if not apply:
        return report
    with engine.begin() as conn:
        if report.rows_to_delete:
            result = conn.execute(text(
                f"DELETE FROM factor_values WHERE id NOT IN ("
                f"SELECT keep_id FROM (SELECT MAX(id) AS keep_id FROM factor_values GROUP BY {KEY}) AS kept)"))
            report.deleted = result.rowcount or 0
        if not report.index_existed:
            conn.execute(text(f"CREATE UNIQUE INDEX {INDEX_NAME} ON factor_values ({KEY})"))
            report.index_created = True
    return report


def ensure_unique_key(engine) -> DedupReport:
    """Startup migration: create the unique index when there is nothing to delete; otherwise only report."""
    report = DedupReport(index_existed=has_unique_key(engine))
    if report.index_existed:
        return report
    report = find_duplicates(engine)
    if report.rows_to_delete:
        return report                                   # needs an explicit --apply
    with engine.begin() as conn:
        conn.execute(text(f"CREATE UNIQUE INDEX {INDEX_NAME} ON factor_values ({KEY})"))
    report.index_created = True
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="delete duplicates and create the unique index")
    parser.add_argument("--db", default="sql_server", help="database type for get_database_url (default sql_server)")
    args = parser.parse_args(argv)
    from sqlalchemy import create_engine
    from src.infrastructure.database.settings import get_database_url
    engine = create_engine(get_database_url(args.db))
    report = deduplicate(engine, apply=args.apply)
    print(report.summary())
    if not args.apply and report.rows_to_delete:
        print("dry run — nothing deleted; rerun with --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
