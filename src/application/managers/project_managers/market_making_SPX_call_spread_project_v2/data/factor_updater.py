"""
FactorUpdater — per-bar factor refresh of the SPX call spread universe.

Replaces ModelTrainer.train_complete_pipeline -> BaseModelTrainer._prepare_factor_data
of the original project, with two differences:

* entities are created once (``ensure_entities``) instead of at every bar;
* the refresh runs on the ALGORITHM's MarketDataHistoryService, whose frontier is
  advanced to the bar time first, so factor resolution happens at the bar's
  time, the same way in backtest and live.

The resolved values are stored by the factor-value pipeline
(``_create_or_get_factor_value_batch``); nothing is returned to the strategy.
"""

import logging
from typing import Any, Dict, List, Optional


class FactorUpdater:

    def __init__(self, history_service, universe: Dict[Any, Any], factor_groups: List[Dict[str, Any]],
                 bar_size_setting: str, duration_str: str, log=None):
        self.history_service = history_service
        self.universe = universe
        self.factor_groups = factor_groups
        self.bar_size_setting = bar_size_setting
        self.duration_str = duration_str
        self.entities: List[Any] = []
        self.logger = logging.getLogger(self.__class__.__name__)
        self.log = log or self.logger.info

    @property
    def market_data_service(self):
        return self.history_service.market_data_service

    def ensure_entities(self) -> List[Any]:
        """Create / get every universe entity (same rules as BaseModelTrainer._prepare_factor_data).

        A dict entry is a container (``args``) plus its ``components``; a list entry
        is a list of tickers (or ticker specs) of one entity class.
        """
        entities: List[Any] = []
        mds = self.market_data_service
        for entity_class, entity_list in self.universe.items():
            if isinstance(entity_list, dict):
                repo = mds.entity_service.repository_factory.get_local_repository(entity_class)
                container = repo._create_or_get(**entity_list.get('args', {}))
                if container:
                    entities.append(container)
                for component_class, tickers in entity_list['components'].items():
                    for ticker in tickers:
                        component = mds.create_entity_from_ticker_item(ticker, component_class)
                        if component:
                            entities.append(component)
            else:
                for ticker in entity_list:
                    entity = mds.create_entity_from_ticker_item(ticker, entity_class)
                    if entity:
                        entities.append(entity)
                    else:
                        name = getattr(entity_class, '__name__', entity_class)
                        self.log(f"Universe entity not created: {name} {ticker}")
        self.entities = entities
        return entities

    def update(self, time) -> Optional[Any]:
        """Advance the frontier to ``time`` and resolve / store every factor of every entity."""
        self.history_service.set_frontier(time)
        if not self.entities or not self.factor_groups:
            return None
        return self.history_service._create_or_get_factor_value_batch(
            factor_groups=self.factor_groups, entities=self.entities, date=time,
            duration_str=self.duration_str, bar_size_setting=self.bar_size_setting,
        )
