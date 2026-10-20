"""
Observation quality and provenance (BI-025) — pure domain, no persistence or broker types.

Every stored factor value (an *observation*: a raw market-data value or a derived one) can carry:

  ObservationProvenance   what it is and where it comes from: instrument, field, source, the provider's
                          data type (TRADES, MIDPOINT, ...), frequency, observation / receipt / ingestion
                          times, its explicit quality status and the validations behind it, and — for a
                          derived value — the observations it was computed from, the transformation and the
                          policy version used
  QualityRequirement      what a consumer accepts (statuses, data types, maximum age at the decision time)
  QualityRequirement.check -> Eligibility: eligible or not, with the reasons

Rules enforced at construction (invalid provenance cannot be created):
  - the status is explicit; VALID is not allowed with a failed validation;
  - INVALID / REJECTED need a reason (a rejection reason or a failed validation);
  - a derived observation names its inputs and its transformation;
  - receipt and ingestion never precede the observation time.

Observations are referenced by the natural key of stored values: (factor, entity type, entity id, date).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import FrozenSet, Optional, Tuple


class ObservationStatus(str, Enum):
    VALID = "valid"            # passed every validation its policy requires
    INVALID = "invalid"        # failed a validation (kept, never used where validity is required)
    STALE = "stale"            # valid when observed, too old for its intended use
    MISSING = "missing"        # expected but not received (a gap record, no value)
    ESTIMATED = "estimated"    # not observed: filled / modelled under an explicit policy
    REJECTED = "rejected"      # refused at ingestion (malformed, placeholder, out of policy)


class SourceDataType(str, Enum):
    """The provider's kind of data behind a value (IBKR whatToShow names), or CALCULATED for derived values."""
    TRADES = "TRADES"
    MIDPOINT = "MIDPOINT"
    BID = "BID"
    ASK = "ASK"
    BID_ASK = "BID_ASK"
    ADJUSTED_LAST = "ADJUSTED_LAST"
    HISTORICAL_VOLATILITY = "HISTORICAL_VOLATILITY"
    OPTION_IMPLIED_VOLATILITY = "OPTION_IMPLIED_VOLATILITY"
    REBATE_RATE = "REBATE_RATE"
    FEE_RATE = "FEE_RATE"
    YIELD_BID = "YIELD_BID"
    YIELD_ASK = "YIELD_ASK"
    YIELD_BID_ASK = "YIELD_BID_ASK"
    YIELD_LAST = "YIELD_LAST"
    SCHEDULE = "SCHEDULE"
    CALCULATED = "CALCULATED"


@dataclass(frozen=True)
class ObservationRef:
    """Natural key of a stored value."""
    factor_id: int
    entity_type: str
    entity_id: int
    observed_at: datetime

    def __post_init__(self):
        if self.factor_id <= 0 or self.entity_id <= 0:
            raise ValueError("factor_id and entity_id must be positive")
        if not self.entity_type:
            raise ValueError("entity_type is required")


@dataclass(frozen=True)
class ValidationResult:
    rule: str                  # e.g. "positive_price", "bid_le_ask", "max_spread_bps"
    passed: bool
    reason: str = ""           # why it failed (required when passed is False)

    def __post_init__(self):
        if not self.rule:
            raise ValueError("a validation needs a rule name")
        if not self.passed and not self.reason:
            raise ValueError(f"failed validation {self.rule!r} needs a reason")


@dataclass(frozen=True)
class ObservationProvenance:
    observation: ObservationRef
    field: str                                   # e.g. "close", "mid_price", "delta"
    source: str                                  # e.g. "ibkr", "calculated"
    data_type: SourceDataType
    frequency: str                               # Factor.FREQUENCIES key, e.g. "1d", "8h"
    status: ObservationStatus
    received_at: Optional[datetime] = None       # when the provider's response arrived
    ingested_at: Optional[datetime] = None       # when it was stored
    validations: Tuple[ValidationResult, ...] = ()
    rejection_reason: str = ""
    inputs: Tuple[ObservationRef, ...] = ()      # derived values: what they were computed from
    transformation: str = ""                     # derived values: the factor / rule that computed them
    policy_version: str = ""                     # validation / source policy in force
    selection: str = ""                          # raw values: why this data type (preferred / fallback, BI-026)

    def __post_init__(self):
        if not self.field or not self.source or not self.frequency:
            raise ValueError("field, source and frequency are required")
        if not isinstance(self.status, ObservationStatus):
            raise ValueError(f"status must be an ObservationStatus, got {self.status!r}")
        if not isinstance(self.data_type, SourceDataType):
            raise ValueError(f"data_type must be a SourceDataType, got {self.data_type!r}")
        failed = [v for v in self.validations if not v.passed]
        if self.status is ObservationStatus.VALID and failed:
            raise ValueError(f"VALID with failed validations: {[v.rule for v in failed]}")
        if self.status in (ObservationStatus.INVALID, ObservationStatus.REJECTED) and not (failed or self.rejection_reason):
            raise ValueError(f"{self.status.value} needs a rejection reason or a failed validation")
        if self.is_derived and (not self.inputs or not self.transformation):
            raise ValueError("a derived observation needs its inputs and its transformation")
        observed = self.observation.observed_at
        for name in ("received_at", "ingested_at"):
            moment = getattr(self, name)
            if moment is not None and _naive(moment) < _naive(observed):
                raise ValueError(f"{name} ({moment}) precedes the observation time ({observed})")

    @property
    def is_derived(self) -> bool:
        return self.data_type is SourceDataType.CALCULATED

    @property
    def failed_validations(self) -> Tuple[ValidationResult, ...]:
        return tuple(v for v in self.validations if not v.passed)


@dataclass(frozen=True)
class Eligibility:
    eligible: bool
    reasons: Tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return self.eligible


@dataclass(frozen=True)
class QualityRequirement:
    """What a calculation accepts. The defaults accept only VALID observations of any data type and age."""
    accepted_statuses: FrozenSet[ObservationStatus] = frozenset({ObservationStatus.VALID})
    accepted_data_types: Optional[FrozenSet[SourceDataType]] = None      # None: any
    max_age: Optional[timedelta] = None                                   # observation age at decision time

    def check(self, provenance: Optional[ObservationProvenance], decision_time: datetime) -> Eligibility:
        if provenance is None:
            return Eligibility(False, ("no provenance recorded: quality unknown",))
        reasons = []
        if provenance.status not in self.accepted_statuses:
            detail = f" ({provenance.rejection_reason})" if provenance.rejection_reason else ""
            reasons.append(f"status {provenance.status.value}{detail} not accepted")
        if self.accepted_data_types is not None and provenance.data_type not in self.accepted_data_types:
            reasons.append(f"data type {provenance.data_type.value} not accepted")
        observed = _naive(provenance.observation.observed_at)
        if observed > _naive(decision_time):
            reasons.append(f"observed at {observed}, after the decision time {decision_time}")
        elif self.max_age is not None and _naive(decision_time) - observed > self.max_age:
            reasons.append(f"older than {self.max_age} at {decision_time}")
        return Eligibility(not reasons, tuple(reasons))


def _naive(moment: datetime) -> datetime:
    """Comparable form: aware times in UTC without tzinfo; naive times as stored (same convention as
    FactorValueModel dates, see tests/contracts/test_orm_schema.py)."""
    if moment.tzinfo is None:
        return moment
    return moment.astimezone(timezone.utc).replace(tzinfo=None)
