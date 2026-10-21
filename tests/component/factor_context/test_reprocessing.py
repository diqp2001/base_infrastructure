"""
BI-028 slices 2 + 4: an upstream correction marks every value computed from it STALE (via factor_value_lineage);
a STALE derived value is recomputed on its next read, never reused. Seeded SQLite market (factor_world.py).
"""

import pytest

from src.domain.entities.factor.observation_quality import ObservationRef, ObservationStatus as S
from src.infrastructure.models.factor.factor_value import FactorValueModel
from tests.component.factor_context.factor_catalog import factor_classes
from tests.component.factor_context.factor_world import LAST_BAR, T, FactorWorld

pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture
def world():
    w = FactorWorld()
    yield w
    w.close()


def factor(name):
    return dict(factor_classes())[name]


def close_ref(world, day=LAST_BAR):
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    close = world.s.query(CompanyShareFactorModel).filter_by(name="close", frequency="1d").first()
    return ObservationRef(close.id, "CompanyShare", world.share["AAPL"].id, day)


def value_ref(world, cls):
    return ObservationRef(world.definition(cls).id, "CompanyShare", world.share["AAPL"].id, T)


def correct(world, ref, value):
    """An upstream correction through the repository (the way a re-ingestion replaces a stored value)."""
    repo = world.f.factor_value_local_repo
    row = (world.s.query(FactorValueModel)
           .filter_by(factor_id=ref.factor_id, entity_id=ref.entity_id, entity_type=ref.entity_type,
                      date=ref.observed_at).one())
    stored = repo.get_by_id(row.id)
    stored.value = value
    assert repo.update(stored) is not None


def provenance(world):
    return world.f.observation_provenance_local_repo


def test_an_unchanged_derived_value_is_reused(world):
    mid = factor("CompanyShareMidPriceFactor")
    world.resolve(mid, world.share["AAPL"])
    value, deps = world.resolve(mid, world.share["AAPL"])
    assert deps is None and value == pytest.approx(world.closes["AAPL"][-1])     # calculate() not called again


def test_a_correction_lists_and_invalidates_every_dependent(world):
    value_cls = factor("CompanyShareValueFactor")
    world.resolve(value_cls, world.share["AAPL"])
    affected = provenance(world).dependents(close_ref(world))
    assert len(affected) >= 2 and affected[-1] == value_ref(world, value_cls)    # the mid price first, then the value
    assert close_ref(world) in provenance(world).get(affected[0]).inputs

    correct(world, close_ref(world), "999.0")
    for ref in affected:
        stale = provenance(world).get(ref)
        assert stale.status is S.STALE and stale.failed_validations[0].rule == "inputs_current"
    assert provenance(world).get(close_ref(world)) is None or \
        provenance(world).get(close_ref(world)).status is not S.STALE                # the corrected input itself is not


def test_after_a_correction_the_next_read_recomputes_from_the_corrected_input(world):
    """Acceptance (5): the re-read equals what a run on an empty derived store gives — no forced resolution."""
    value_cls = factor("CompanyShareValueFactor")
    before, _ = world.resolve(value_cls, world.share["AAPL"])
    assert before == pytest.approx(world.closes["AAPL"][-1])
    correct(world, close_ref(world), "999.0")
    after, deps = world.resolve(value_cls, world.share["AAPL"])
    assert deps is not None and after == pytest.approx(999.0)
    assert provenance(world).get(value_ref(world, value_cls)).status is S.VALID      # recomputed: current again


def test_a_seeded_stale_derived_value_is_not_used(world):
    mid = factor("CompanyShareMidPriceFactor")
    world.resolve(mid, world.share["AAPL"])
    row = world.s.query(FactorValueModel).filter_by(factor_id=world.definition(mid).id,
                                                    entity_id=world.share["AAPL"].id, date=T).one()
    row.value = "1.0"                                    # a wrong stored value ...
    world.s.commit()
    assert provenance(world).mark_stale([value_ref(world, mid)], "seeded") == 1      # ... known to be stale
    value, deps = world.resolve(mid, world.share["AAPL"])
    assert deps is not None and value == pytest.approx(world.closes["AAPL"][-1])


def test_reprocessing_adds_no_rows(world):
    value_cls = factor("CompanyShareValueFactor")
    world.resolve(value_cls, world.share["AAPL"])
    rows = world.s.query(FactorValueModel).count()
    correct(world, close_ref(world), "999.0")
    world.resolve(value_cls, world.share["AAPL"])
    world.resolve(value_cls, world.share["AAPL"])
    assert world.s.query(FactorValueModel).count() == rows


def test_a_new_policy_version_reprocesses_derived_values_from_stored_raw_data(world):
    """Slice 3: values computed under another PROVENANCE_POLICY_VERSION are recomputed (no IBKR call: the raw
    close is read from the store), once — the recomputed value carries the current version and is reused after."""
    mid = factor("CompanyShareMidPriceFactor")
    world.resolve(mid, world.share["AAPL"])
    service = type(world.service)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(service, "PROVENANCE_POLICY_VERSION", "provenance-v2")
        value, deps = world.resolve(mid, world.share["AAPL"])
        assert deps is not None and value == pytest.approx(world.closes["AAPL"][-1])
        assert provenance(world).get(value_ref(world, mid)).policy_version == "provenance-v2"
        assert world.resolve(mid, world.share["AAPL"])[1] is None                 # idempotent: reused afterwards


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "NaN"])
def test_a_non_finite_output_is_not_stored(world, bad):
    """BI-032: NaN / inf from calculate() is a failed calculation — no value, nothing stored, not a zero."""
    from unittest.mock import patch
    mid = factor("CompanyShareMidPriceFactor")
    rows = world.s.query(FactorValueModel).count()
    with patch.object(mid, "calculate", lambda self, *a, **k: bad):
        fv = world.service.resolve_factor_value(world.definition(mid), world.share["AAPL"], T)
    assert fv is None and world.s.query(FactorValueModel).count() == rows
