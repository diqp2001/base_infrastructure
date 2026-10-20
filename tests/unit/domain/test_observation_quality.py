"""
BI-025 (domain slice): observation quality status and provenance are explicit, consistent, and decide
eligibility for a consumer. No database, no broker.
"""

from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import given, strategies as st

from src.domain.entities.factor.observation_quality import (
    Eligibility, ObservationProvenance, ObservationRef, ObservationStatus as S, QualityRequirement,
    SourceDataType as D, ValidationResult,
)

T0 = datetime(2026, 8, 24, 9, 30)                           # bar start (exchange-local, naive)
DECISION = datetime(2026, 8, 24, 16, 0)


def ref(factor_id=14, entity_type="CompanyShareOption", entity_id=6, at=T0):
    return ObservationRef(factor_id, entity_type, entity_id, at)


def raw(status=S.VALID, data_type=D.MIDPOINT, validations=(), **kw):
    return ObservationProvenance(observation=ref(), field="close", source="ibkr", data_type=data_type,
                                 frequency="8h", status=status, validations=validations, **kw)


PASS = ValidationResult("positive_price", True)
FAIL = ValidationResult("bid_le_ask", False, "bid 117.2 > ask 117.0 (crossed)")


# ---- valid observations ---------------------------------------------------------------------

def test_a_valid_observation_is_eligible_by_default():
    p = raw(validations=(PASS,), received_at=T0 + timedelta(hours=7), ingested_at=T0 + timedelta(hours=7))
    assert QualityRequirement().check(p, DECISION) == Eligibility(True)


def test_status_is_explicit_not_inferred_from_the_value():
    with pytest.raises(ValueError, match="ObservationStatus"):
        raw(status="valid")


# ---- invalid observations -------------------------------------------------------------------

def test_valid_with_a_failed_validation_cannot_be_built():
    with pytest.raises(ValueError, match="VALID with failed validations"):
        raw(validations=(PASS, FAIL))


@pytest.mark.parametrize("status", [S.INVALID, S.REJECTED])
def test_invalid_or_rejected_needs_a_reason(status):
    with pytest.raises(ValueError, match="needs a rejection reason"):
        raw(status=status)
    assert raw(status=status, rejection_reason="zero placeholder price").status is status
    assert raw(status=status, validations=(FAIL,)).failed_validations == (FAIL,)


def test_invalid_data_is_never_treated_as_valid():
    p = raw(status=S.INVALID, validations=(FAIL,))
    result = QualityRequirement().check(p, DECISION)
    assert not result and result.reasons == ("status invalid not accepted",)


def test_a_failed_validation_needs_its_reason():
    with pytest.raises(ValueError, match="needs a reason"):
        ValidationResult("max_spread_bps", False)


# ---- missing metadata -----------------------------------------------------------------------

def test_no_provenance_means_unknown_quality_not_valid():
    result = QualityRequirement().check(None, DECISION)
    assert not result and "quality unknown" in result.reasons[0]


@pytest.mark.parametrize("missing", ["field", "source", "frequency"])
def test_required_metadata(missing):
    kwargs = dict(observation=ref(), field="close", source="ibkr", data_type=D.TRADES, frequency="1d",
                  status=S.VALID)
    kwargs[missing] = ""
    with pytest.raises(ValueError, match="required"):
        ObservationProvenance(**kwargs)


def test_reference_needs_a_positive_identity():
    with pytest.raises(ValueError):
        ObservationRef(0, "CompanyShare", 5, T0)
    with pytest.raises(ValueError):
        ObservationRef(14, "", 5, T0)


def test_receipt_cannot_precede_the_observation():
    with pytest.raises(ValueError, match="received_at"):
        raw(received_at=T0 - timedelta(minutes=1))


# ---- derived values and lineage -------------------------------------------------------------

def test_a_derived_value_names_its_inputs_and_transformation():
    with pytest.raises(ValueError, match="inputs and its transformation"):
        ObservationProvenance(observation=ref(factor_id=394, at=DECISION), field="delta", source="calculated",
                              data_type=D.CALCULATED, frequency="1d", status=S.VALID)
    delta = ObservationProvenance(
        observation=ref(factor_id=394, at=DECISION), field="delta", source="calculated", data_type=D.CALCULATED,
        frequency="1d", status=S.VALID, inputs=(ref(), ref(5, "CompanyShare", 5)),
        transformation="CompanyShareOptionDeltaFactor", policy_version="quality-v1")
    assert delta.is_derived and len(delta.inputs) == 2


# ---- consumer requirements ------------------------------------------------------------------

def test_a_consumer_can_require_a_data_type():
    marks_only = QualityRequirement(accepted_data_types=frozenset({D.MIDPOINT}))
    assert marks_only.check(raw(data_type=D.MIDPOINT), DECISION)
    result = marks_only.check(raw(data_type=D.TRADES), DECISION)
    assert not result and result.reasons == ("data type TRADES not accepted",)


def test_stale_by_age_for_the_intended_use():
    intraday = QualityRequirement(max_age=timedelta(hours=8))
    assert intraday.check(raw(), DECISION)
    assert not intraday.check(raw(), DECISION + timedelta(days=1))


def test_an_observation_after_the_decision_is_never_eligible():
    result = QualityRequirement().check(raw(), T0 - timedelta(minutes=1))
    assert not result and "after the decision time" in result.reasons[0]


def test_estimated_values_only_when_accepted_explicitly():
    estimated = raw(status=S.ESTIMATED)
    assert not QualityRequirement().check(estimated, DECISION)
    assert QualityRequirement(accepted_statuses=frozenset({S.VALID, S.ESTIMATED})).check(estimated, DECISION)


def test_aware_and_naive_times_compare_in_utc():
    aware = ObservationProvenance(observation=ref(at=datetime(2026, 8, 24, 13, 30, tzinfo=timezone.utc)),
                                  field="close", source="ibkr", data_type=D.MIDPOINT, frequency="8h", status=S.VALID)
    assert QualityRequirement().check(aware, datetime(2026, 8, 24, 14, 0))
    assert not QualityRequirement().check(aware, datetime(2026, 8, 24, 13, 0))


@given(status=st.sampled_from(list(S)), data_type=st.sampled_from([d for d in D if d is not D.CALCULATED]))
def test_only_accepted_statuses_are_ever_eligible(status, data_type):
    """Property: whatever the status / data type, eligibility under the default requirement means VALID."""
    p = raw(status=status, data_type=data_type, rejection_reason="r" if status in (S.INVALID, S.REJECTED) else "")
    assert bool(QualityRequirement().check(p, DECISION)) == (status is S.VALID)
