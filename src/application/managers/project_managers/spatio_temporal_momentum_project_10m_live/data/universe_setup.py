"""
UniverseSetup — resolves the configured tickers to CompanyShare entities and
registers them as a Universe with UniverseConstituent rows.
"""

import logging
from datetime import date
from typing import Dict, List, Optional, Tuple

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMConfiguration,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_universe import (
    STMUniverseService,
)


class UniverseSetup:

    def __init__(self, factory, config: STMConfiguration):
        self.config = config
        self.service = STMUniverseService(factory, config.universe)
        self.logger = logging.getLogger(self.__class__.__name__)

    def tickers(self) -> List[str]:
        return list(self.config.universe.tickers or [])

    def register(self, ticker_to_entity: Optional[Dict[str, int]] = None,
                 start_date: Optional[date] = None) -> Tuple[object, Dict[str, int], List[str]]:
        """
        Returns (universe, {ticker: entity_id} in configured order, missing tickers).
        Tickers without a CompanyShare entity are reported, not silently dropped.
        """
        tickers = self.tickers()
        if ticker_to_entity is None:
            ticker_to_entity, missing = self.service.resolve_entities(tickers)
        else:
            missing = [t for t in tickers if t not in ticker_to_entity]
        ordered = {t: ticker_to_entity[t] for t in tickers if t in ticker_to_entity}
        if missing:
            self.logger.warning(f"Universe tickers without CompanyShare entity: {missing}")
        universe = self.service.ensure_universe(ordered, start_date or date.today())
        return universe, ordered, missing
