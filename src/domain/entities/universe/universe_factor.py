"""
src/domain/entities/universe/universe_factor.py

UniverseFactor — membership of one factor in a Universe (membership only: no weight, no rank).
"""

from __future__ import annotations

from typing import Optional

from src.domain.entities.entity import Entity


class UniverseFactor(Entity):

    def __init__(self, universe_id: Optional[int], factor_id: int, id: Optional[int] = None):
        super().__init__(id)
        if factor_id is None:
            raise ValueError("a universe factor needs a factor_id")
        self.universe_id = universe_id
        self.factor_id = int(factor_id)

    def __repr__(self) -> str:
        return f"UniverseFactor(id={self.id}, universe_id={self.universe_id}, factor_id={self.factor_id})"
