"""
ORM schema and mapping rules (no database server needed).

- importing src.infrastructure.models alone registers every table any repository uses
  (create_all on a fresh database builds the whole schema);
- every table has a primary key and every foreign key resolves to an existing column;
- the only timezone-aware column (factor_values.date) is returned naive by its mapper, the
  convention every other datetime column follows on every backend.
"""

import subprocess
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from tests.architecture.import_cycles import ROOT

SCRIPT = r"""
import json, sys
from src.infrastructure.models import ModelBase
registered = set(ModelBase.metadata.tables)
from tests.repositories.repository_checks import all_repository_classes
all_repository_classes()
print(json.dumps(sorted(set(ModelBase.metadata.tables) - registered)))
"""


def _metadata():
    from src.infrastructure.models import ModelBase
    return ModelBase.metadata


class TestSchemaRegistration:

    def test_models_package_registers_every_table(self):
        run = subprocess.run([sys.executable, "-c", SCRIPT], cwd=ROOT, capture_output=True, text=True, timeout=300,
                             env={**__import__("os").environ, "PYTHONPATH": ROOT})
        assert run.returncode == 0, run.stderr[-3000:]
        late = __import__("json").loads(run.stdout.strip().splitlines()[-1])
        assert late == [], f"tables registered only when a repository module is imported: {late}"

    def test_every_table_has_a_primary_key(self):
        assert [t for t, table in _metadata().tables.items() if not table.primary_key.columns] == []

    def test_every_foreign_key_resolves(self):
        broken = []
        for name, table in _metadata().tables.items():
            for fk in table.foreign_keys:
                try:
                    fk.column
                except Exception as e:
                    broken.append(f"{name}.{fk.parent.name} -> {fk.target_fullname} ({type(e).__name__})")
        assert broken == []

    def test_timezone_aware_columns_are_known(self):
        aware = sorted(f"{t}.{c.name}" for t, table in _metadata().tables.items() for c in table.columns
                       if getattr(c.type, "timezone", False))
        assert aware == ["factor_values.date"], "a new timezone-aware column needs the naive-date mapping too"


class TestFactorValueDateMapping:

    @pytest.fixture
    def to_domain(self):
        from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
        return lambda date: FactorValueMapper.to_domain(SimpleNamespace(
            id=1, factor_id=2, date=date, value="1.5", entity_type="CompanyShare", entity_id=3, currency_id=None)).date

    def test_naive_dates_pass_through(self, to_domain):
        assert to_domain(datetime(2026, 1, 5, 9, 30)) == datetime(2026, 1, 5, 9, 30)

    def test_sql_server_offset_zero_becomes_naive(self, to_domain):
        """Regression: SQL Server DATETIMEOFFSET returned the naive bar time labelled UTC."""
        assert to_domain(datetime(2026, 1, 5, 9, 30, tzinfo=timezone.utc)) == datetime(2026, 1, 5, 9, 30)

    def test_other_offsets_are_normalised_to_utc(self, to_domain):
        eastern = timezone(timedelta(hours=-5))
        assert to_domain(datetime(2026, 1, 5, 9, 30, tzinfo=eastern)) == datetime(2026, 1, 5, 14, 30)
