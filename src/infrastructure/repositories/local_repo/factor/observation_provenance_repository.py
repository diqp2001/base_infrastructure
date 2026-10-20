"""
ObservationProvenancePort on the database (BI-025 slice 2): provenance rows in factor_value_provenance, lineage
edges in factor_value_lineage, both keyed by the stored factor value (factor_values.id). Values are addressed by
their natural key (factor, entity type, entity id, date), as in ObservationRef. Conversion: ObservationProvenanceMapper.
Registered in RepositoryFactory as 'ObservationProvenance'.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.domain.entities.factor.observation_quality import ObservationProvenance, ObservationRef
from src.domain.ports.factor.observation_provenance_port import ObservationProvenancePort
from src.infrastructure.models.factor.factor_value import FactorValueModel
from src.infrastructure.models.factor.factor_value_provenance import FactorValueLineageModel, FactorValueProvenanceModel
from src.infrastructure.repositories.mappers.factor.observation_provenance_mapper import ObservationProvenanceMapper


class ObservationProvenanceRepository(ObservationProvenancePort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = ObservationProvenanceMapper()

    # ------------------------------------------------------------------ port
    def get(self, observation: ObservationRef) -> Optional[ObservationProvenance]:
        row = self._value_row(observation)
        if row is None:
            return None
        return self.mapper.to_domain(observation, self.session.get(FactorValueProvenanceModel, row.id),
                                     self._input_refs(row.id))

    def record(self, provenance: ObservationProvenance) -> ObservationProvenance:
        """Store (or replace) the provenance of a stored value and its lineage edges. The value and every input
        must already be stored (LookupError otherwise). Idempotent."""
        row = self._value_row(provenance.observation)
        if row is None:
            raise LookupError(f"no stored factor value for {provenance.observation}: store the value first")
        input_ids = []
        for ref in provenance.inputs:
            input_row = self._value_row(ref)
            if input_row is None:
                raise LookupError(f"input {ref} of {provenance.observation} is not a stored factor value")
            input_ids.append(input_row.id)
        model = self.mapper.to_orm(provenance, row.id, self.session.get(FactorValueProvenanceModel, row.id))
        self.session.add(model)
        self.session.query(FactorValueLineageModel).filter_by(factor_value_id=row.id).delete(synchronize_session=False)
        for position, input_id in enumerate(input_ids):
            self.session.add(FactorValueLineageModel(factor_value_id=row.id, input_factor_value_id=input_id,
                                                     position=position))
        self.session.commit()
        return provenance

    def lineage(self, observation: ObservationRef) -> List[ObservationProvenance]:
        """Provenance of every input, transitively, breadth first (direct inputs first), no duplicates. Inputs
        without recorded provenance are not listed (their quality is unknown)."""
        row = self._value_row(observation)
        if row is None:
            return []
        result, seen, frontier = [], {row.id}, [row.id]
        while frontier:
            next_frontier = []
            for value_id in frontier:
                for input_id, ref in self._input_edges(value_id):
                    if input_id in seen:
                        continue
                    seen.add(input_id)
                    next_frontier.append(input_id)
                    provenance = self.mapper.to_domain(ref, self.session.get(FactorValueProvenanceModel, input_id),
                                                       self._input_refs(input_id))
                    if provenance is not None:
                        result.append(provenance)
            frontier = next_frontier
        return result

    # ------------------------------------------------------------------ helpers
    def _value_row(self, ref: ObservationRef) -> Optional[FactorValueModel]:
        return (self.session.query(FactorValueModel)
                .filter(FactorValueModel.factor_id == ref.factor_id,
                        FactorValueModel.entity_id == ref.entity_id,
                        FactorValueModel.entity_type == ref.entity_type,
                        FactorValueModel.date == ref.observed_at)
                .first())

    def _input_edges(self, value_id: int):
        rows = (self.session.query(FactorValueLineageModel.input_factor_value_id, FactorValueModel)
                .join(FactorValueModel, FactorValueModel.id == FactorValueLineageModel.input_factor_value_id)
                .filter(FactorValueLineageModel.factor_value_id == value_id)
                .order_by(FactorValueLineageModel.position).all())
        return [(input_id, self.mapper.ref(value)) for input_id, value in rows]

    def _input_refs(self, value_id: int):
        return tuple(ref for _, ref in self._input_edges(value_id))
