"""
Universe handling for Spatio-Temporal Momentum.

``select_reference_universe`` reproduces train_multivariate.ipynb cell 7:
    np.random.seed(SEED)
    for each sector (dict order): np.random.choice(eligible_assets, N, replace=False)
The reference first keeps only stocks with more than LENGTH_THRESHOLD rows of
history; pass ``eligible`` to apply the same filter with local data.

``STMUniverseService`` registers the selection as a Universe with ordered
UniverseConstituent rows through the existing repositories.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMUniverseConfig,
)


def select_reference_universe(sectors: Dict[str, List[str]], n_per_sector: int = 5, seed: int = 42,
                              eligible: Optional[Iterable[str]] = None) -> List[str]:
    rs = np.random.RandomState(seed)  # identical stream to np.random.seed(seed) + np.random.choice
    eligible_set = set(eligible) if eligible is not None else None
    picked: List[str] = []
    for sector, assets in sectors.items():
        pool = [a for a in assets if eligible_set is None or a in eligible_set]
        if len(pool) < n_per_sector:
            raise ValueError(f"Sector '{sector}' has {len(pool)} eligible assets, need {n_per_sector}")
        picked.extend(str(a) for a in rs.choice(pool, n_per_sector, replace=False))
    return picked


class STMUniverseService:

    def __init__(self, factory, config: STMUniverseConfig):
        self.factory = factory
        self.config = config

    def resolve_entities(self, tickers: List[str]) -> Tuple[Dict[str, int], List[str]]:
        """Map tickers to existing CompanyShare entity ids; returns (found, missing)."""
        repo = self.factory.get_local_repository("CompanyShare")
        found: Dict[str, int] = {}
        missing: List[str] = []
        for t in tickers:
            entity = repo.get_by_symbol(t) if repo is not None else None
            if entity is not None and getattr(entity, "id", None) is not None:
                found[t] = int(entity.id)
            else:
                missing.append(t)
        return found, missing

    def ensure_universe(self, ticker_to_entity: Dict[str, int], start_date: date):
        """Create (or get) the Universe and one constituent per entity."""
        from src.domain.entities.universe.universe import Universe
        from src.domain.entities.universe.universe_constituent import UniverseConstituent

        universe = self.factory.investment_universe_local_repo._create_or_get(
            Universe,
            self.config.name,
            entity_type=self.config.entity_type,
            description="Spatio-Temporal Momentum research universe (reference sector sample)",
        )
        if universe is None:
            raise RuntimeError(f"Could not create universe '{self.config.name}'")
        constituent_repo = self.factory.universe_constituent_local_repo
        for ticker, entity_id in ticker_to_entity.items():
            constituent_repo._create_or_get(
                UniverseConstituent,
                f"{universe.id}_{entity_id}",
                universe_id=universe.id,
                entity_id=entity_id,
                entity_type=self.config.entity_type,
                start_date=start_date,
            )
        return universe

    def active_entity_ids(self, as_of: date) -> List[int]:
        universe = self.factory.investment_universe_local_repo.get_by_name(self.config.name)
        if universe is None:
            return []
        constituents = self.factory.universe_constituent_local_repo.get_active_by_universe(universe.id, as_of)
        return sorted(int(c.entity_id) for c in constituents)
