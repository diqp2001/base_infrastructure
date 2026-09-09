"""
src/domain/entities/universe/universe.py

Universe domain entity — a named collection of financial entities for investment or analysis.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from src.domain.entities.entity import Entity


class Universe(Entity):
    """
    A reusable investment universe: a named set of financial entities (e.g. S&P 500,
    Russell 1000, custom basket) used by portfolio construction, factor calculation,
    ML training, and backtesting.
    """

    def __init__(
        self,
        name: str,
        id: Optional[int] = None,
        description: Optional[str] = None,
        entity_type: Optional[str] = None,
        currency_id: Optional[int] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        super().__init__(id)
        self.name = name
        self.description = description
        self.entity_type = entity_type      # e.g. "CompanyShare", "IndexFuture"
        self.currency_id = currency_id
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"Universe(id={self.id}, name='{self.name}', entity_type={self.entity_type})"
