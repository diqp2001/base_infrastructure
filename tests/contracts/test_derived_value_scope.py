"""
BI-006 slice 2b: derived_values_all_or_nothing — on failure the derived (source 'calculated') factor values an
operation inserted are deleted and the ones it overwrote are restored; raw values are kept. SQLite and the SQL
Server test database (`backend` fixture).
"""

from datetime import datetime

import pytest

from src.domain.entities.factor.factor_value import FactorValue
from src.infrastructure.database.derived_value_scope import derived_values_all_or_nothing
from src.infrastructure.models.factor.factor import CompanyShareFactorModel
from src.infrastructure.models.factor.factor_value import FactorValueModel
from src.infrastructure.repositories.local_repo.factor.factor_value_repository import FactorValueRepository

T = datetime(2026, 1, 6, 16, 0)


@pytest.fixture
def world(backend):
    session = backend.session()
    factors = {}
    for source in ("ibkr", "calculated"):
        f = CompanyShareFactorModel(name=f"scope-{source}", group="price", subgroup="ohlc", frequency="1d",
                                    data_type="numeric", source=source, definition="scope test",
                                    factor_type="company_share_factor")
        session.add(f)
        session.commit()
        factors[source] = f.id
    repo = FactorValueRepository(session, factory=None)
    yield session, repo, factors
    session.rollback()
    session.query(FactorValueModel).filter(FactorValueModel.factor_id.in_(factors.values())).delete(
        synchronize_session=False)
    session.query(CompanyShareFactorModel).filter(CompanyShareFactorModel.id.in_(factors.values())).delete(
        synchronize_session=False)
    session.commit()
    session.close()


def value(factor_id, entity_id, v):
    return FactorValue(id=None, factor_id=factor_id, entity=None, entity_id=entity_id, entity_type="CompanyShare",
                       date=T, value=v)


def stored(session, factor_id):
    session.expire_all()
    return sorted((r.entity_id, r.value) for r in session.query(FactorValueModel).filter_by(factor_id=factor_id))


def test_a_failure_undoes_derived_writes_and_keeps_raw_ones(world):
    session, repo, f = world
    old = repo.add(value(f["calculated"], 1, "10.0"))                     # derived value from an earlier run
    with pytest.raises(RuntimeError, match="valuation failed"):
        with derived_values_all_or_nothing(session):
            repo.add(value(f["ibkr"], 1, "150.0"))                        # raw price fetched on the way
            repo.update(FactorValue(id=old.id, factor_id=f["calculated"], entity=None, entity_id=1,
                                    entity_type="CompanyShare", date=T, value="11.0"))   # derived overwritten
            repo.add(value(f["calculated"], 2, "20.0"))                   # derived inserted
            raise RuntimeError("valuation failed")
    assert stored(session, f["calculated"]) == [(1, "10.0")]              # insert undone, overwrite restored
    assert stored(session, f["ibkr"]) == [(1, "150.0")]                   # raw kept


def test_success_keeps_everything(world):
    session, repo, f = world
    with derived_values_all_or_nothing(session):
        repo.add(value(f["ibkr"], 1, "150.0"))
        repo.add(value(f["calculated"], 1, "10.0"))
    assert stored(session, f["calculated"]) == [(1, "10.0")]
    assert stored(session, f["ibkr"]) == [(1, "150.0")]


def test_a_nested_scope_joins_the_outer_one(world):
    session, repo, f = world
    with pytest.raises(RuntimeError):
        with derived_values_all_or_nothing(session):
            with derived_values_all_or_nothing(session):                  # e.g. a sub-portfolio valuation
                repo.add(value(f["calculated"], 1, "10.0"))
            raise RuntimeError("outer failed after the inner scope ended")
    assert stored(session, f["calculated"]) == []
