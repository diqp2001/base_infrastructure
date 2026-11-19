"""
src/domain/entities/universe/investment_universe.py

InvestmentUniverse — the projects' point-in-time investment universe, a child type of Universe.

On top of the Universe (name, description, version, UniverseFinancialAsset / UniverseFactor members) it keeps what
the projects already use: the entity type of its constituents and a currency. Its dated (and, for ETF holdings,
weighted) membership history stays in ``UniverseConstituent`` rows: an ETF's holding weight is the ETF's
composition, read by the dispersion factors, not a property of universe membership.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.domain.entities.universe.universe import Universe


class InvestmentUniverse(Universe):

    def __init__(
        self,
        name: str,
        id: Optional[int] = None,
        description: Optional[str] = None,
        entity_type: Optional[str] = None,
        currency_id: Optional[int] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        version: int = 1,
        **members,
    ):
        super().__init__(name=name, id=id, description=description, universe_type="InvestmentUniverse",
                         version=version, created_at=created_at, updated_at=updated_at, **members)
        self.entity_type = entity_type      # e.g. "CompanyShare", "IndexFuture"
        self.currency_id = currency_id

    def __repr__(self) -> str:
        return f"InvestmentUniverse(id={self.id}, name='{self.name}', entity_type={self.entity_type})"
