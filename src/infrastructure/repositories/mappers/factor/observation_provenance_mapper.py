"""
Mapper between ObservationProvenance (domain) and FactorValueProvenanceModel (ORM) — BI-025.
Lineage edges are stored separately (FactorValueLineageModel) and passed in as ObservationRefs.
"""

import json
from datetime import timezone
from typing import Dict, List, Optional, Tuple

from src.domain.entities.factor.observation_quality import (
    ObservationProvenance, ObservationRef, ObservationStatus, SourceDataType, ValidationResult,
)
from src.infrastructure.models.factor.factor_value import FactorValueModel
from src.infrastructure.models.factor.factor_value_provenance import FactorValueProvenanceModel


class ObservationProvenanceMapper:

    @staticmethod
    def ref(value: FactorValueModel) -> ObservationRef:
        """Natural key of a stored factor value (dates compared naive, see _naive)."""
        return ObservationRef(value.factor_id, value.entity_type, value.entity_id, _naive(value.date))

    @staticmethod
    def to_domain(ref: ObservationRef, model: Optional[FactorValueProvenanceModel],
                  inputs: Tuple[ObservationRef, ...] = ()) -> Optional[ObservationProvenance]:
        if model is None:
            return None
        validations: List[Dict] = json.loads(model.validations) if model.validations else []
        return ObservationProvenance(
            observation=ref, field=model.field, source=model.source,
            data_type=SourceDataType(model.data_type), frequency=model.frequency,
            status=ObservationStatus(model.status),
            received_at=_naive(model.received_at), ingested_at=_naive(model.ingested_at),
            validations=tuple(ValidationResult(v["rule"], v["passed"], v.get("reason", "")) for v in validations),
            rejection_reason=model.rejection_reason or "", inputs=tuple(inputs),
            transformation=model.transformation or "", policy_version=model.policy_version or "",
            selection=model.selection or "")

    @staticmethod
    def to_orm(provenance: ObservationProvenance, factor_value_id: int,
               model: Optional[FactorValueProvenanceModel] = None) -> FactorValueProvenanceModel:
        """Fill (or create) the provenance row of the stored value `factor_value_id`."""
        model = model or FactorValueProvenanceModel(factor_value_id=factor_value_id)
        model.field = provenance.field
        model.source = provenance.source
        model.data_type = provenance.data_type.value
        model.frequency = provenance.frequency
        model.status = provenance.status.value
        model.received_at = _naive(provenance.received_at)
        model.ingested_at = _naive(provenance.ingested_at)
        model.rejection_reason = provenance.rejection_reason or None
        model.transformation = provenance.transformation or None
        model.policy_version = provenance.policy_version or None
        model.selection = provenance.selection or None
        model.validations = (json.dumps([{"rule": v.rule, "passed": v.passed, "reason": v.reason}
                                         for v in provenance.validations]) if provenance.validations else None)
        return model


def _naive(moment):
    """SQL Server returns stored datetimes with a UTC offset, SQLite as written: compare in naive form."""
    if moment is None or getattr(moment, "tzinfo", None) is None:
        return moment
    return moment.astimezone(timezone.utc).replace(tzinfo=None)
