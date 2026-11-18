"""
IndexUniverseSetup - registers a point-in-time index universe (IndexMembership) in the database: one Universe and
one UniverseConstituent row per membership interval (start / end dates from IndexMembership) of every symbol given an
entity id - the members, and the ETF itself when its id is given (entity ETFShare, never removed). Rows already stored
are kept (idempotent).
"""

import logging
from typing import Dict, List, Tuple

from src.application.services.dispersion.index_membership import IndexMembership
from src.domain.entities.universe.universe import Universe
from src.domain.entities.universe.universe_constituent import UniverseConstituent


class IndexUniverseSetup:

    def __init__(self, factory, membership: IndexMembership):
        self.factory = factory
        self.membership = membership
        self.logger = logging.getLogger(self.__class__.__name__)

    def register(self, entity_ids: Dict[str, int]) -> Tuple[object, List[str]]:
        """(universe, symbols without an entity). ``entity_ids``: {symbol: entity id} of the ETF and the members."""
        m = self.membership
        universe = self.factory.investment_universe_local_repo._create_or_get(
            Universe, m.universe.name, entity_type=m.universe.entity_type, description=m.universe.description)
        if universe is None:
            raise RuntimeError(f"Could not create universe '{m.universe.name}'")
        repo = self.factory.universe_constituent_local_repo
        stored = {(int(c.entity_id), c.start_date) for c in repo.get_by_universe(universe.id)}
        missing = []
        for row in m.constituents:
            symbol = m.symbol_of(row.entity_id)
            entity_id = entity_ids.get(symbol)
            if entity_id is None:
                missing.append(symbol)
                continue
            if (int(entity_id), row.start_date) in stored:
                continue
            repo.add(UniverseConstituent(universe_id=universe.id, entity_id=int(entity_id),
                                         entity_type=row.entity_type, start_date=row.start_date,
                                         end_date=row.end_date))
        if missing:
            self.logger.warning(f"Universe symbols without entity (not registered): {sorted(set(missing))}")
        return universe, sorted(set(missing))
