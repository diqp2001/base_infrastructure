"""
src/domain/entities/universe/universe_constituent.py

UniverseConstituent domain entity — historical membership of a financial entity in a Universe.
"""

from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from src.domain.entities.entity import Entity


class UniverseConstituent(Entity):
    """
    Records the membership of one financial entity in a Universe over a time window.

    An entity may enter and leave a universe multiple times; each interval is a
    separate UniverseConstituent row (end_date=None means currently active).
    Weight is optional — some universes are equally weighted or cap-weighted
    externally.
    """

    def __init__(
        self,
        universe_id: int,
        entity_id: int,
        entity_type: str,
        start_date: date,
        id: Optional[int] = None,
        end_date: Optional[date] = None,
        weight: Optional[float] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        super().__init__(id)
        self.universe_id = universe_id
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.start_date = start_date
        self.end_date = end_date
        self.weight = weight
        self.created_at = created_at
        self.updated_at = updated_at

    @property
    def is_active(self) -> bool:
        return self.end_date is None

    def __repr__(self) -> str:
        return (
            f"UniverseConstituent(id={self.id}, universe_id={self.universe_id}, "
            f"entity_id={self.entity_id}, entity_type={self.entity_type}, "
            f"start={self.start_date}, end={self.end_date})"
        )
