"""
BI-025 slice 3: provenance used by the resolution path (seeded SQLite market, factor_world.py).

  - a derived value records the stored values it was computed from (lineage), including lookback windows;
  - a factor declaring a `quality_requirement` is not computed from ineligible inputs (no provenance, rejected);
  - IBKR raw ingestion records the data type, receipt / ingestion time and validation of each stored value.
"""

import math
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.observation_quality import (
    ObservationProvenance, ObservationRef, ObservationStatus as S, QualityRequirement, SourceDataType as D,
    ValidationResult,
)
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


def close_ref(world, ticker="AAPL", day=LAST_BAR):
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    close = world.s.query(CompanyShareFactorModel).filter_by(name="close", frequency="1d").first()
    return ObservationRef(close.id, "CompanyShare", world.share[ticker].id, day)


def value_ref(world, cls, entity, when=T):
    definition = world.definition(cls)
    return ObservationRef(definition.id, type(entity).__name__.removesuffix("Model"), entity.id, when)


def provenance(world):
    return world.f.observation_provenance_local_repo


# ---- lineage --------------------------------------------------------------------------------

def test_a_derived_value_records_the_value_it_read(world):
    cls = factor("CompanyShareMidPriceFactor")
    value, _ = world.resolve(cls, world.share["AAPL"])
    assert value == pytest.approx(world.closes["AAPL"][-1])
    stored = provenance(world).get(value_ref(world, cls, world.share["AAPL"]))
    assert stored is not None and stored.is_derived and stored.status is S.VALID
    assert stored.inputs == (close_ref(world),)                       # Friday's close, the bar it used
    assert stored.transformation == "CompanyShareMidPriceFactor"


def test_a_window_factor_records_every_bar_of_its_window(world):
    cls = factor("CompanySharePriceVsMA20Factor")
    value, _ = world.resolve(cls, world.share["AAPL"])
    assert value is not None and math.isfinite(value)
    stored = provenance(world).get(value_ref(world, cls, world.share["AAPL"]))
    assert [ref.observed_at for ref in stored.inputs] == world.days[-20:]


def test_lineage_follows_derived_inputs(world):
    value_cls, mid_cls = factor("CompanyShareValueFactor"), factor("CompanyShareMidPriceFactor")
    value, _ = world.resolve(value_cls, world.share["AAPL"])
    assert value is not None
    chain = provenance(world).lineage(value_ref(world, value_cls, world.share["AAPL"]))
    mids = [p for p in chain if p.transformation == mid_cls.__name__]
    assert mids and mids[0].observation.entity_id == world.share["AAPL"].id      # the mid price it was built on
    assert close_ref(world) in mids[0].inputs                                     # ... which read Friday's close


# ---- quality gate ---------------------------------------------------------------------------

def raw_provenance(ref, status=S.VALID, validations=()):
    return ObservationProvenance(observation=ref, field="close", source="ibkr", data_type=D.TRADES, frequency="1d",
                                 status=status, validations=validations)


def test_inputs_without_provenance_are_refused_when_the_factor_requires_quality(world):
    cls = factor("CompanyShareMidPriceFactor")
    with patch.object(cls, "quality_requirement", QualityRequirement(), create=True):
        value, captured = world.resolve(cls, world.share["AAPL"])
    assert value is None and captured is None                         # calculate() never called


def test_a_valid_input_is_accepted(world):
    cls = factor("CompanyShareMidPriceFactor")
    provenance(world).record(raw_provenance(close_ref(world)))
    with patch.object(cls, "quality_requirement", QualityRequirement(), create=True):
        value, _ = world.resolve(cls, world.share["AAPL"])
    assert value == pytest.approx(world.closes["AAPL"][-1])


def test_a_rejected_input_is_refused(world):
    cls = factor("CompanyShareMidPriceFactor")
    provenance(world).record(raw_provenance(
        close_ref(world), status=S.REJECTED, validations=(ValidationResult("positive_price", False, "price <= 0"),)))
    with patch.object(cls, "quality_requirement", QualityRequirement(), create=True):
        value, _ = world.resolve(cls, world.share["AAPL"])
    assert value is None


def test_without_a_requirement_nothing_changes(world):
    cls = factor("CompanyShareMidPriceFactor")
    assert getattr(cls, "quality_requirement", None) is None
    value, _ = world.resolve(cls, world.share["AAPL"])
    assert value == pytest.approx(world.closes["AAPL"][-1])


# ---- IBKR ingestion -------------------------------------------------------------------------

def test_ibkr_ingestion_records_data_type_and_validation(world):
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository
    close = world.s.query(CompanyShareFactorModel).filter_by(name="close", frequency="1d").first()
    close_factor = SimpleNamespace(id=close.id, name="close", group="price", frequency="1d")
    days = [datetime(2026, 1, 6), datetime(2026, 1, 7)]
    stored = [world.f.factor_value_local_repo.add(FactorValue(
        id=None, factor_id=close.id, entity=None, entity_id=world.share["AAPL"].id, entity_type="CompanyShare",
        date=day, value=v)) for day, v in zip(days, ("181.5", "0.0"))]
    IBKRFactorValueRepository._record_raw_provenance(SimpleNamespace(factory=world.f), stored, [close_factor],
                                                     "MIDPOINT")
    good = provenance(world).get(close_ref(world, day=days[0]))
    bad = provenance(world).get(close_ref(world, day=days[1]))
    assert (good.status, good.data_type, good.source) == (S.VALID, D.MIDPOINT, "ibkr")
    assert good.received_at is not None and good.received_at >= days[0]
    assert bad.status is S.REJECTED and bad.failed_validations[0].rule == "positive_price"


def test_ibkr_ingestion_flags_an_inconsistent_bar(world):
    """BI-030: a bar whose close is above its high is stored but INVALID (every field of it); a consistent bar of
    the same response stays VALID."""
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository
    factors, stored = [], []
    good_day, bad_day = datetime(2026, 1, 6), datetime(2026, 1, 7)
    bars = {good_day: dict(open="100", high="102", low="99", close="101"),
            bad_day: dict(open="100", high="102", low="99", close="105")}
    for name in ("open", "high", "low", "close"):
        model = world.s.query(CompanyShareFactorModel).filter_by(name=name, frequency="1d").first()
        factors.append(SimpleNamespace(id=model.id, name=name, group="price", frequency="1d"))
        for day, bar in bars.items():
            stored.append(world.f.factor_value_local_repo.add(FactorValue(
                id=None, factor_id=model.id, entity=None, entity_id=world.share["AAPL"].id,
                entity_type="CompanyShare", date=day, value=bar[name])))
    IBKRFactorValueRepository._record_raw_provenance(SimpleNamespace(factory=world.f), stored, factors, "TRADES")
    for f in factors:
        good = provenance(world).get(ObservationRef(f.id, "CompanyShare", world.share["AAPL"].id, good_day))
        bad = provenance(world).get(ObservationRef(f.id, "CompanyShare", world.share["AAPL"].id, bad_day))
        assert good.status is S.VALID
        assert bad.status is S.INVALID and [v.rule for v in bad.failed_validations] == ["close_within_range"]
