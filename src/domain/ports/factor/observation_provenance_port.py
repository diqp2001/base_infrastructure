"""
Port for reading and recording observation provenance (BI-025). Implemented by the persistence slice of BI-025
(infrastructure, on the existing factor-value tables); consumers depend on this interface only.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.factor.observation_quality import ObservationProvenance, ObservationRef


class ObservationProvenancePort(ABC):

    @abstractmethod
    def get(self, observation: ObservationRef) -> Optional[ObservationProvenance]:
        """Provenance of one stored value, or None when none was recorded (quality unknown)."""

    @abstractmethod
    def record(self, provenance: ObservationProvenance) -> ObservationProvenance:
        """Store the provenance of a value (idempotent for the same observation and content)."""

    @abstractmethod
    def lineage(self, observation: ObservationRef) -> List[ObservationProvenance]:
        """Every observation the value was computed from, transitively (inputs first, no duplicates)."""

    @abstractmethod
    def dependents(self, observation: ObservationRef) -> List[ObservationRef]:
        """Every stored value computed from this one, transitively (direct dependents first, no duplicates) —
        what an upstream correction affects (BI-028)."""

    @abstractmethod
    def mark_stale(self, observations: List[ObservationRef], reason: str) -> int:
        """Mark derived values STALE (their inputs changed): they are recomputed, not reused, on the next read.
        Returns how many were marked."""

    def invalidate_dependents(self, observation: ObservationRef, reason: str) -> List[ObservationRef]:
        """An observation was corrected: mark everything computed from it STALE; returns the affected values."""
        affected = self.dependents(observation)
        if affected:
            self.mark_stale(affected, reason)
        return affected
