"""
BI-025 slice 2: ObservationProvenancePort on the database (ObservationProvenanceRepository), through the
RepositoryFactory. SQLite and the SQL Server test database (`backend` fixture).
"""

from datetime import datetime

import pytest

from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.observation_quality import (
    ObservationProvenance, ObservationRef, ObservationStatus as S, QualityRequirement, SourceDataType as D,
    ValidationResult,
)
from src.domain.ports.factor.observation_provenance_port import ObservationProvenancePort
from src.infrastructure.models.factor.factor import CompanyShareFactorModel
from src.infrastructure.models.factor.factor_value import FactorValueModel
from src.infrastructure.models.factor.factor_value_provenance import FactorValueLineageModel, FactorValueProvenanceModel

BAR = datetime(2026, 8, 24, 9, 30)
DECISION = datetime(2026, 8, 24, 16, 0)


@pytest.fixture
def world(backend):
    with backend.factory() as (factory, session):
        ids = {}
        for name, source in (("close", "ibkr"), ("mid_price", "calculated"), ("delta", "calculated")):
            f = CompanyShareFactorModel(name=f"prov-{name}", group="price", subgroup="ohlc", frequency="1d",
                                        data_type="numeric", source=source, definition="provenance test",
                                        factor_type="company_share_factor")
            session.add(f)
            session.commit()
            ids[name] = f.id
        values = factory.factor_value_local_repo
        refs = {}
        for name, when, v in (("close", BAR, "116.6"), ("mid_price", DECISION, "116.6"), ("delta", DECISION, "0.66")):
            values.add(FactorValue(id=None, factor_id=ids[name], entity=None, entity_id=6,
                                   entity_type="CompanyShareOption", date=when, value=v))
            refs[name] = ObservationRef(ids[name], "CompanyShareOption", 6, when)
        yield factory, session, refs
        session.rollback()
        fv_ids = [i for (i,) in session.query(FactorValueModel.id).filter(FactorValueModel.factor_id.in_(ids.values()))]
        session.query(FactorValueLineageModel).filter(FactorValueLineageModel.factor_value_id.in_(fv_ids)).delete(
            synchronize_session=False)
        session.query(FactorValueProvenanceModel).filter(FactorValueProvenanceModel.factor_value_id.in_(fv_ids)).delete(
            synchronize_session=False)
        session.query(FactorValueModel).filter(FactorValueModel.id.in_(fv_ids)).delete(synchronize_session=False)
        session.query(CompanyShareFactorModel).filter(CompanyShareFactorModel.id.in_(ids.values())).delete(
            synchronize_session=False)
        session.commit()


def raw(ref):
    return ObservationProvenance(observation=ref, field="close", source="ibkr", data_type=D.MIDPOINT, frequency="8h",
                                 status=S.VALID, validations=(ValidationResult("positive_price", True),),
                                 received_at=datetime(2026, 8, 24, 17, 31), ingested_at=datetime(2026, 8, 24, 17, 31),
                                 policy_version="quality-v1")


def derived(ref, inputs, field, transformation):
    return ObservationProvenance(observation=ref, field=field, source="calculated", data_type=D.CALCULATED,
                                 frequency="1d", status=S.VALID, inputs=tuple(inputs), transformation=transformation,
                                 policy_version="quality-v1")


def test_the_factory_serves_the_port(world):
    factory, _, _ = world
    assert isinstance(factory.observation_provenance_local_repo, ObservationProvenancePort)


def test_provenance_round_trips_with_its_explicit_status(world):
    factory, _, refs = world
    repo = factory.observation_provenance_local_repo
    assert repo.get(refs["close"]) is None                                   # nothing recorded: quality unknown
    repo.record(raw(refs["close"]))
    stored = repo.get(refs["close"])
    assert stored == raw(refs["close"])
    assert QualityRequirement(accepted_data_types=frozenset({D.MIDPOINT})).check(stored, DECISION)


def test_rejected_observation_keeps_its_reason(world):
    factory, _, refs = world
    repo = factory.observation_provenance_local_repo
    rejected = ObservationProvenance(observation=refs["close"], field="close", source="ibkr", data_type=D.TRADES,
                                     frequency="8h", status=S.REJECTED,
                                     validations=(ValidationResult("bid_le_ask", False, "crossed: bid > ask"),))
    repo.record(rejected)
    stored = repo.get(refs["close"])
    assert stored.status is S.REJECTED and stored.failed_validations[0].reason == "crossed: bid > ask"
    assert not QualityRequirement().check(stored, DECISION)


def test_lineage_is_transitive_and_ordered(world):
    factory, _, refs = world
    repo = factory.observation_provenance_local_repo
    repo.record(raw(refs["close"]))
    repo.record(derived(refs["mid_price"], [refs["close"]], "mid_price", "CompanyShareOptionMidPriceFactor"))
    repo.record(derived(refs["delta"], [refs["mid_price"]], "delta", "CompanyShareOptionDeltaFactor"))
    assert repo.get(refs["delta"]).inputs == (refs["mid_price"],)
    assert [p.observation for p in repo.lineage(refs["delta"])] == [refs["mid_price"], refs["close"]]


def test_recording_twice_is_idempotent(world):
    factory, session, refs = world
    repo = factory.observation_provenance_local_repo
    repo.record(raw(refs["close"]))
    repo.record(derived(refs["mid_price"], [refs["close"]], "mid_price", "CompanyShareOptionMidPriceFactor"))
    repo.record(derived(refs["mid_price"], [refs["close"]], "mid_price", "CompanyShareOptionMidPriceFactor"))
    assert session.query(FactorValueLineageModel).count() >= 1
    assert repo.get(refs["mid_price"]).inputs == (refs["close"],)
    assert len(repo.lineage(refs["mid_price"])) == 1


def test_unknown_value_or_input_fails_clearly(world):
    factory, _, refs = world
    repo = factory.observation_provenance_local_repo
    missing = ObservationRef(refs["close"].factor_id, "CompanyShareOption", 6, datetime(2026, 8, 21, 9, 30))
    with pytest.raises(LookupError, match="store the value first"):
        repo.record(raw(missing))
    with pytest.raises(LookupError, match="is not a stored factor value"):
        repo.record(derived(refs["mid_price"], [missing], "mid_price", "CompanyShareOptionMidPriceFactor"))


# ---- BI-028: upstream corrections ------------------------------------------------------------

def test_dependents_are_listed_transitively_nearest_first(world):
    factory, _, refs = world
    repo = factory.observation_provenance_local_repo
    repo.record(raw(refs["close"]))
    repo.record(derived(refs["mid_price"], [refs["close"]], "mid_price", "CompanyShareOptionMidPriceFactor"))
    repo.record(derived(refs["delta"], [refs["mid_price"]], "delta", "CompanyShareOptionDeltaFactor"))
    assert repo.dependents(refs["close"]) == [refs["mid_price"], refs["delta"]]
    assert repo.dependents(refs["delta"]) == []


def test_a_corrected_value_marks_its_dependents_stale(world):
    factory, _, refs = world
    repo = factory.observation_provenance_local_repo
    repo.record(raw(refs["close"]))
    repo.record(derived(refs["mid_price"], [refs["close"]], "mid_price", "CompanyShareOptionMidPriceFactor"))
    repo.record(derived(refs["delta"], [refs["mid_price"]], "delta", "CompanyShareOptionDeltaFactor"))
    values = factory.factor_value_local_repo
    stored = next(v for v in values.get_all() if (v.factor_id, v.date) == (refs["close"].factor_id, BAR))
    stored.value = "117.0"
    values.update(stored)
    for ref in (refs["mid_price"], refs["delta"]):
        stale = repo.get(ref)
        assert stale.status is S.STALE and "117.0" in stale.failed_validations[0].reason
        assert stale.inputs                                                         # lineage kept
    assert repo.get(refs["close"]).status is S.VALID
    repo.record(derived(refs["mid_price"], [refs["close"]], "mid_price", "CompanyShareOptionMidPriceFactor"))
    assert repo.get(refs["mid_price"]).status is S.VALID                            # recomputed: current again


def test_an_unchanged_update_invalidates_nothing(world):
    factory, _, refs = world
    repo = factory.observation_provenance_local_repo
    repo.record(raw(refs["close"]))
    repo.record(derived(refs["mid_price"], [refs["close"]], "mid_price", "CompanyShareOptionMidPriceFactor"))
    values = factory.factor_value_local_repo
    stored = next(v for v in values.get_all() if (v.factor_id, v.date) == (refs["close"].factor_id, BAR))
    values.update(stored)
    assert repo.get(refs["mid_price"]).status is S.VALID
