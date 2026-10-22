"""
CSMModelTrainer — Misbuffet BaseModelTrainer of the cross-sectional momentum project (same wiring as the STM one).

* BaseModelTrainer.create_factors creates the signal factor listed in config['factors'].
* build_cycle wires the time-driven CSMTradingCycle onto the algorithm's own MarketDataService /
  MarketDataHistoryService (frontier).
"""

import logging
import os
from typing import Any, Dict

import pandas as pd

from src.application.managers.project_managers.cross_sectionnal_project.config import build_csm_configuration
from src.application.managers.project_managers.cross_sectionnal_project.data.price_ingestion import (
    DailyHistoryUpdater,
)
from src.application.managers.project_managers.cross_sectionnal_project.data.universe_setup import UniverseSetup
from src.application.services.data.backtest_preload.backtest_data_preload_service import BacktestDataPreloadService
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import benchmark_entity_types
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_preload import (
    extra_series,
    preload_series,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_model_provider import (
    CSMModelProvider,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_trading_cycle import (
    CSMTradingCycle,
)
from src.application.services.misbuffet.engine.base_model_trainer import BaseModelTrainer

PRELOAD_FILE = "preload.csv"                       # coverage of every preloaded series (results_dir)


class CSMModelTrainer(BaseModelTrainer):

    def __init__(self, database_service, config: Dict[str, Any]):
        super().__init__(database_service, config)
        self.csm_config = build_csm_configuration(config)
        CSMModelProvider.default_config = self.csm_config
        self.logger = logging.getLogger(self.__class__.__name__)

    def ensure_factors(self) -> Dict[str, Any]:
        return self.create_factors(self.config.get("factors", []))

    def preload(self, market_data_service, updater: DailyHistoryUpdater, log=None):
        """Every series of the run (shares' TRADES, their implied volatility, SPY, IRX), history start .. backtest
        end, BEFORE the first bar (BacktestDataPreloadService): the engine and the cycle then read locally and do not
        call IBKR during the run. Coverage per series -> <results_dir>/preload.csv."""
        service = BacktestDataPreloadService(market_data_service, log=log or self.logger.info)
        results = service.preload(preload_series(self.csm_config, self.config["bar_size_setting"]),
                                  start=self.config["price_history_start"], end=self.config["backtest_end"])
        try:
            os.makedirs(self.config["results_dir"], exist_ok=True)
            service.to_frame(results).to_csv(os.path.join(self.config["results_dir"], PRELOAD_FILE), index=False)
        except OSError as e:
            self.logger.warning(f"Could not write the preload report: {e}")
        updater.mark_imported()                       # the history is there: no second full import at bar 1
        return results

    def build_cycle(self, market_data_service, history_service, factory, log=None) -> CSMTradingCycle:
        """Entities, universe and the trading cycle, bound to the algorithm's Misbuffet services."""
        history_start = self.config["price_history_start"]
        client = getattr(getattr(market_data_service.entity_service, "repository_factory", None), "ibkr_client", None)
        connection = getattr(client, "ib_connection", None)
        if client is None or not getattr(connection, "connected_flag", False):
            raise RuntimeError(
                "IBKR / TWS is not connected, so no daily closes can be imported. Check that TWS is running "
                "on 127.0.0.1:7497 and that no other session is already connected with the same client id."
            )
        # benchmarks (SPY for the relative features, the IRX T-bill index for the band rate) and named series of the
        # shares (their IBKR implied volatility) are imported but never traded
        tickers = list(self.csm_config.universe.tickers)
        types = benchmark_entity_types(self.csm_config.features)
        updater = DailyHistoryUpdater(market_data_service, tickers, history_start,
                                      extra_series=extra_series(self.csm_config))
        ticker_to_entity = updater.ensure_entities()
        if self.config.get("preload_data", False):
            self.preload(market_data_service, updater, log=log)
        benchmark_entities = {s: ticker_to_entity[s] for s in types if s in ticker_to_entity}
        universe_setup = UniverseSetup(factory, self.csm_config)
        universe, ordered, missing = universe_setup.register(
            ticker_to_entity, start_date=pd.Timestamp(history_start).date())
        if missing:
            self.logger.warning(f"Universe tickers without entity (excluded): {missing}")
        self.ensure_factors()
        return CSMTradingCycle(
            factory=factory,
            config=self.csm_config,
            history_service=history_service,
            ticker_to_entity=ordered,
            history_start=history_start,
            retrain_every_days=self.config.get("retrain_every_days", 21),
            data_updater=updater,
            universe_service=universe_setup.service,
            universe_id=getattr(universe, "id", None),
            log=log or self.logger.info,
            benchmark_entities=benchmark_entities,
        )
