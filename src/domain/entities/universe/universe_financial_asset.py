"""
src/domain/entities/universe/universe_financial_asset.py

UniverseFinancialAsset — membership of one financial asset in a Universe.

Membership only: no weight, no rank, no allocation (a universe is a list of constituents, not a portfolio).
``start_date`` / ``end_date`` are optional: None / None = a member with no dated window (owner's choice
2026-11-19); a dated window says when the asset belonged to the universe (end_date exclusive, None = still a member).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from src.domain.entities.entity import Entity


class UniverseFinancialAsset(Entity):

    def __init__(self, universe_id: Optional[int], financial_asset_id: int, id: Optional[int] = None,
                 start_date: Optional[date] = None, end_date: Optional[date] = None):
        super().__init__(id)
        if financial_asset_id is None:
            raise ValueError("a universe financial asset needs a financial_asset_id")
        if start_date is not None and end_date is not None and end_date <= start_date:
            raise ValueError(f"end_date {end_date} must be after start_date {start_date}")
        self.universe_id = universe_id
        self.financial_asset_id = int(financial_asset_id)
        self.start_date = start_date
        self.end_date = end_date

    def is_member_on(self, day: Optional[date]) -> bool:
        """True when the asset belongs to the universe on ``day`` (None = any time: undated memberships count)."""
        if day is None:
            return True
        return (self.start_date is None or self.start_date <= day) and (self.end_date is None or day < self.end_date)

    def overlaps(self, start_date: Optional[date], end_date: Optional[date]) -> bool:
        """Whether [start_date, end_date) intersects this membership (None = unbounded)."""
        starts_before_other_ends = end_date is None or self.start_date is None or self.start_date < end_date
        other_starts_before_end = start_date is None or self.end_date is None or start_date < self.end_date
        return starts_before_other_ends and other_starts_before_end

    def __repr__(self) -> str:
        window = "" if self.start_date is None and self.end_date is None else f", {self.start_date}..{self.end_date}"
        return (f"UniverseFinancialAsset(id={self.id}, universe_id={self.universe_id}, "
                f"financial_asset_id={self.financial_asset_id}{window})")
