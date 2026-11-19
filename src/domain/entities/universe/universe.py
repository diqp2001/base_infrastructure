"""
src/domain/entities/universe/universe.py

Universe — a reusable, named listing of constituents that a Strategy references (``Strategy.universe_id``).

    Universe
    ├── UniverseFinancialAsset   (financial assets: optional dated membership)
    └── UniverseFactor           (factors)

A universe is a SET of constituents: it holds no weights, ranks, allocations or position sizes (those belong to
portfolio construction / model output). Adding a constituent that is already a member is refused
(DuplicateMembership); for financial assets "already a member" means an overlapping membership window.

Kinds of universe are subclasses (``universe_type`` = the class name): ``InvestmentUniverse`` is the point-in-time
investment universe of the projects (entity type, currency, dated / weighted ``UniverseConstituent`` rows).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Iterable, List, Optional

from src.domain.entities.entity import Entity
from src.domain.entities.universe.universe_factor import UniverseFactor
from src.domain.entities.universe.universe_financial_asset import UniverseFinancialAsset


class DuplicateMembership(ValueError):
    """The constituent is already a member of the universe."""


class Universe(Entity):

    def __init__(
        self,
        name: str,
        id: Optional[int] = None,
        description: Optional[str] = None,
        universe_type: Optional[str] = None,
        version: int = 1,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        financial_assets: Optional[Iterable[UniverseFinancialAsset]] = None,
        factors: Optional[Iterable[UniverseFactor]] = None,
    ):
        super().__init__(id)
        if not (name or "").strip():
            raise ValueError("a universe needs a name")
        if int(version) < 1:
            raise ValueError("a universe version starts at 1")
        self.name = name.strip()
        self.description = description
        self.universe_type = universe_type or type(self).__name__
        self.version = int(version)
        self.created_at = created_at
        self.updated_at = updated_at
        self.financial_assets: List[UniverseFinancialAsset] = []
        self.factors: List[UniverseFactor] = []
        for member in financial_assets or ():
            self._add_asset_member(member)
        for member in factors or ():
            self._add_factor_member(member)

    # -- financial assets -----------------------------------------------------------------------------------------
    def add_financial_asset(self, financial_asset_id: int, start_date: Optional[date] = None,
                            end_date: Optional[date] = None) -> UniverseFinancialAsset:
        return self._add_asset_member(UniverseFinancialAsset(self.id, financial_asset_id,
                                                             start_date=start_date, end_date=end_date))

    def _add_asset_member(self, member: UniverseFinancialAsset) -> UniverseFinancialAsset:
        for existing in self.financial_assets:
            if (existing.financial_asset_id == member.financial_asset_id
                    and existing.overlaps(member.start_date, member.end_date)):
                raise DuplicateMembership(
                    f"financial asset {member.financial_asset_id} is already a member of universe '{self.name}' "
                    f"({existing.start_date}..{existing.end_date})")
        member.universe_id = self.id
        self.financial_assets.append(member)
        return member

    def remove_financial_asset(self, financial_asset_id: int, start_date: Optional[date] = None) -> bool:
        """Remove the membership of the asset (the one starting at ``start_date`` when the asset has several)."""
        before = len(self.financial_assets)
        self.financial_assets = [m for m in self.financial_assets
                                 if not (m.financial_asset_id == financial_asset_id
                                         and (start_date is None or m.start_date == start_date))]
        return len(self.financial_assets) < before

    def financial_asset_ids(self, on: Optional[date] = None) -> List[int]:
        """Member asset ids (on ``on`` when given), in insertion order, each once."""
        seen: List[int] = []
        for m in self.financial_assets:
            if m.is_member_on(on) and m.financial_asset_id not in seen:
                seen.append(m.financial_asset_id)
        return seen

    def has_financial_asset(self, financial_asset_id: int, on: Optional[date] = None) -> bool:
        return financial_asset_id in self.financial_asset_ids(on)

    # -- factors --------------------------------------------------------------------------------------------------
    def add_factor(self, factor_id: int) -> UniverseFactor:
        return self._add_factor_member(UniverseFactor(self.id, factor_id))

    def _add_factor_member(self, member: UniverseFactor) -> UniverseFactor:
        if any(f.factor_id == member.factor_id for f in self.factors):
            raise DuplicateMembership(f"factor {member.factor_id} is already a member of universe '{self.name}'")
        member.universe_id = self.id
        self.factors.append(member)
        return member

    def remove_factor(self, factor_id: int) -> bool:
        before = len(self.factors)
        self.factors = [f for f in self.factors if f.factor_id != factor_id]
        return len(self.factors) < before

    def factor_ids(self) -> List[int]:
        return [f.factor_id for f in self.factors]

    # -------------------------------------------------------------------------------------------------------------
    def __repr__(self) -> str:
        return (f"Universe(id={self.id}, name='{self.name}', type={self.universe_type}, v{self.version}, "
                f"assets={len(self.financial_assets)}, factors={len(self.factors)})")
