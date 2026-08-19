"""
Generic data loader base class shared across all project managers.

Every project's DataLoader should extend BaseDataLoader.  The standard
EntityService / MarketDataService / MarketDataHistoryService / FactorService
chain is wired here so subclasses don't repeat the initialisation boilerplate.
"""

import logging
from typing import NamedTuple

from src.application.services.data.entities.entity_service import EntityService
from src.application.services.data.entities.factor.factor_service import FactorService
from src.application.services.database_service.database_service import DatabaseService
from src.application.services.misbuffet.data.market_data_history_service import MarketDataHistoryService
from src.application.services.misbuffet.data.market_data_service import MarketDataService


class DataServices(NamedTuple):
    """Typed container for the four core data services."""
    entity_service: EntityService
    market_data_service: MarketDataService
    history_service: MarketDataHistoryService
    database_service: DatabaseService


class BaseDataLoader:
    """
    Standard data-service initialisation pattern used by every project loader.

    Subclasses add project-specific methods (e.g. get_option_chain_data,
    check_spx_data_availability) without duplicating the service wiring.
    """

    def __init__(self, database_service: DatabaseService, factor_manager=None):
        self.database_service = database_service
        self.logger = logging.getLogger(self.__class__.__name__)

        self.financial_asset_service = EntityService(database_service)
        self.financial_asset_service.create_ibkr_repositories()

        self.market_data_service = MarketDataService(self.financial_asset_service)
        self.market_data_history_service = MarketDataHistoryService(self.market_data_service)
        self.factor_data_service = FactorService(database_service)

        # Injected by the algorithm if factor-based entity management is needed
        self.factor_manager = factor_manager

    def get_data_services(self) -> DataServices:
        """Return all services bundled in a typed NamedTuple."""
        return DataServices(
            entity_service=self.financial_asset_service,
            market_data_service=self.market_data_service,
            history_service=self.market_data_history_service,
            database_service=self.database_service,
        )
