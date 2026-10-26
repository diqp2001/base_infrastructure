"""
UniverseSetup — resolves the configured tickers to CompanyShare entities and registers them as a Universe with
UniverseConstituent rows (the STM universe service, which only needs a name and an entity type).
"""

import logging
from datetime import date
from typing import Dict, List, Optional, Tuple

from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
    CSMConfiguration,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_universe import (
    STMUniverseService,
)


class UniverseSetup:

    def __init__(self, factory, config: CSMConfiguration):
        self.config = config
        self.service = STMUniverseService(factory, config.universe)
        self.logger = logging.getLogger(self.__class__.__name__)

    def register(self, ticker_to_entity: Dict[str, int],
                 start_date: Optional[date] = None) -> Tuple[object, Dict[str, int], List[str]]:
        """Returns (universe, {ticker: entity_id} in configured order, tickers without entity)."""
        tickers = list(self.config.universe.tickers or [])
        missing = [t for t in tickers if t not in ticker_to_entity]
        ordered = {t: ticker_to_entity[t] for t in tickers if t in ticker_to_entity}
        if missing:
            self.logger.warning(f"Universe tickers without CompanyShare entity: {missing}")
        universe = self.service.ensure_universe(ordered, start_date or date.today())
        return universe, ordered, missing
