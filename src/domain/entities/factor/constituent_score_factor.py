"""
src/domain/entities/factor/constituent_score_factor.py

ConstituentScoreFactor — a Factor subclass that stores cross-sectional scores,
ML predictions, or signal scores for universe constituents.

Values are stored in the existing factor_values table (factor_id, entity_id,
entity_type, date, value) — no separate persistence table is required.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Optional, List
from src.domain.entities.factor.factor import Factor


class ConstituentScoreFactor(Factor):
    """
    A Factor whose values represent constituent-level scores at a point in time.

    Examples:
    - Cross-sectional momentum rank score
    - ML predicted return (classification probability or regression output)
    - Composite signal score
    - Expected return estimate

    Resolution: Branch B (no calculate_dependencies) — scores are written directly
    by ML pipeline services, not computed by the resolution service.

    Values are stored in factor_values with entity_id = constituent entity id
    and entity_type = constituent entity class name (e.g. "CompanyShare").
    """

    def __init__(
        self,
        name: str = "constituent_score",
        group: str = "fundamental",
        subgroup: Optional[str] = "score",
        frequency: Optional[str] = "1d",
        data_type: Optional[str] = "numeric",
        source: Optional[str] = "calculated",
        definition: Optional[str] = "Cross-sectional constituent score",
        factor_id: Optional[int] = None,
        score_type: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            frequency=frequency,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
            **kwargs,
        )
        self.score_type = score_type  # e.g. "rank", "zscore", "probability", "regression"

    def calculate(self, dependencies: dict) -> Optional[Decimal]:
        """
        Scores are written directly by ML pipeline services; this method is not
        used in normal resolution flow.  Override in subclasses if the score can
        be computed from other factors.
        """
        return None

    def __repr__(self) -> str:
        return (
            f"ConstituentScoreFactor(id={self.id}, name={self.name}, "
            f"score_type={self.score_type})"
        )
