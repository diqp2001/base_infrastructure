




import time
import os
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any

import pandas as pd
from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.project_managers.test_project_data import config
from application.services.misbuffet.data.factor_factory.factor_factory import FactorFactory
from domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from domain.entities.finance.financial_assets.currency import Currency as CurrencyEntity
from domain.entities.finance.financial_assets.equity import FundamentalData, Dividend
from domain.entities.finance.financial_assets.security import MarketData

from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal
from infrastructure.repositories.local_repo.finance.financial_assets.currency_repository import CurrencyRepository as CurrencyRepositoryLocal
from infrastructure.repositories.local_repo.factor.finance.financial_assets.currency_factor_repository import CurrencyFactorRepository
from infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository

class TestProjectDataManager(ProjectManager):
    """
    Test project data manager.
    Handles entity creation (shares, currencies) and factor computation using the FactorFactory.
    """

    def __init__(self):
        super().__init__()

        # Initialize database manager and repositories
        self.setup_database_manager(DatabaseManager(config.CONFIG_TEST['DB_TYPE']))
        self.company_share_repository_local = CompanyShareRepositoryLocal(self.database_manager.session)
        self.currency_repository_local = CurrencyRepositoryLocal(self.database_manager.session)

        # Initialize factor repositories
        self.currency_factor_repository = CurrencyFactorRepository(config.CONFIG_TEST['DB_TYPE'])
        self.share_factor_repository = ShareFactorRepository(config.CONFIG_TEST['DB_TYPE'])

        # ✅ Initialize the factor factory
        self.factor_factory = FactorFactory()

    # -------------------------
    # ENTITY CREATION METHODS
    # -------------------------

    def add_entities(self):
        """Create base entities (shares, currencies) for testing."""
        self.add_shares()
        self.add_currencies()

    def add_shares(self):
        print("add_shares")

    def add_currencies(self):
        print("add_currencies")

    # -------------------------
    # FACTOR COMPUTATION METHODS
    # -------------------------

    def add_shares_factors(self):
        """
        Compute and store share-related factors using the FactorFactory.
        """
        print("add_shares_factors")

        # Example: retrieve historical prices for each share
        shares = self.company_share_repository_local.get_all()
        for share in shares:
            prices = self._get_market_data(share)

            # ✅ Compute factors dynamically using the factory
            ma20 = self.factor_factory.create("moving_average", input_data=prices, window=20)
            momentum = self.factor_factory.create("momentum", input_data=prices, lookback=30)

            # Store computed factors
            self.share_factor_repository.save_factor(share.id, "moving_average_20", ma20)
            self.share_factor_repository.save_factor(share.id, "momentum_30", momentum)

    def add_currencies_factors(self):
        """
        Compute and store currency-related factors using the FactorFactory.
        """
        print("add_currencies_factors")

        currencies = self.currency_repository_local.get_all()
        for currency in currencies:
            fx_series = self._get_market_data(currency)

            # Example of using the same factory for different entity types
            ma10 = self.factor_factory.create("moving_average", input_data=fx_series, window=10)
            momentum = self.factor_factory.create("momentum", input_data=fx_series, lookback=15)

            self.currency_factor_repository.save_factor(currency.id, "ma10", ma10)
            self.currency_factor_repository.save_factor(currency.id, "momentum15", momentum)

    # -------------------------
    # INTERNAL UTILITIES
    # -------------------------

    def _get_market_data(self, entity):
        """
        Placeholder method to fetch a market data series for an entity.
        Replace this with real data retrieval logic.
        """
        print(f"Fetching price data for {entity.name}")
        # Example: use MarketData or repo to get a pandas.Series of prices
        return MarketData(entity).get_price_series()
    