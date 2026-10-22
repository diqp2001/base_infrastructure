"""
STMModelTrainer — Misbuffet BaseModelTrainer for the INTRADAY (10-minute) Spatio-Temporal Momentum
project (same wiring as the SPX project's ModelTrainer).

* BaseModelTrainer.create_factors creates the STM feature and signal factors
  from the factor library entries listed in config['factors'].
* build_cycle wires the time-driven STMTradingCycle onto the algorithm's
  own MarketDataService / MarketDataHistoryService (frontier).
"""

import logging
import os

import pandas as pd
from typing import Any, Dict

from src.application.managers.project_managers.spatio_temporal_momentum_project_10m.config import (
    build_stm_configuration,
)
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m.data.price_ingestion import (
    BarHistoryUpdater,
)
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m.data.universe_setup import (
    UniverseSetup,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_model_provider import (
    SpatioTemporalMomentumModelProvider,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_trading_cycle import (
    STMTradingCycle,
)
from src.application.services.data.backtest_preload.backtest_data_preload_service import (
    BacktestDataPreloadService,
    PreloadSeries,
)
from src.application.services.misbuffet.engine.base_model_trainer import BaseModelTrainer
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare

PRELOAD_FILE = "preload.csv"                       # coverage of every preloaded series (results_dir)


class STMModelTrainer(BaseModelTrainer):

    def __init__(self, database_service, config: Dict[str, Any]):
        super().__init__(database_service, config)
        self.stm_config = build_stm_configuration(config)
        SpatioTemporalMomentumModelProvider.default_config = self.stm_config
        self.logger = logging.getLogger(self.__class__.__name__)

    def ensure_factors(self) -> Dict[str, Any]:
        """Create the feature + signal factors listed in config['factors'] (Misbuffet path)."""
        return self.create_factors(self.config.get("factors", []))

    def preload(self, market_data_service, updater: BarHistoryUpdater, log=None):
        """Every 10-minute TRADES series of the universe, history start .. backtest end, BEFORE the first bar
        (BacktestDataPreloadService): the engine and the cycle then find the bars locally and do not call IBKR
        during the run. Coverage per series -> <results_dir>/preload.csv."""
        service = BacktestDataPreloadService(market_data_service, log=log or self.logger.info)
        series = [PreloadSeries(CompanyShare, t, "TRADES", self.config["bar_size_setting"])
                  for t in self.stm_config.universe.tickers]
        results = service.preload(series, start=self.config["price_history_start"], end=self.config["backtest_end"])
        try:
            os.makedirs(self.config["results_dir"], exist_ok=True)
            service.to_frame(results).to_csv(os.path.join(self.config["results_dir"], PRELOAD_FILE), index=False)
        except OSError as e:
            self.logger.warning(f"Could not write the preload report: {e}")
        updater.mark_imported()                       # the history is there: no second full import at bar 1
        return results

    def build_cycle(self, market_data_service, history_service, factory,
                    log=None) -> STMTradingCycle:
        """Entities, universe and the trading cycle, bound to the algorithm's Misbuffet services."""
        history_start = self.config["price_history_start"]
        client = getattr(getattr(market_data_service.entity_service, "repository_factory", None), "ibkr_client", None)
        connection = getattr(client, "ib_connection", None)
        if client is None or not getattr(connection, "connected_flag", False):
            raise RuntimeError(
                "IBKR / TWS is not connected, so no intraday bars can be imported. Check that TWS is running "
                "on 127.0.0.1:7497 and that no other session (e.g. a debug run of src/main.py) is already "
                "connected with the same client id."
            )
        updater = BarHistoryUpdater(market_data_service, self.stm_config.universe.tickers, history_start,
                                    bar_size_setting=self.config["bar_size_setting"],
                                    bar_minutes=self.stm_config.bar_minutes)
        ticker_to_entity = updater.ensure_entities()
        if self.config.get("preload_data", False):
            self.preload(market_data_service, updater, log=log)
        universe_setup = UniverseSetup(factory, self.stm_config)
        # membership starts at the configured history start (reference universe is static)
        universe, ordered, missing = universe_setup.register(
            ticker_to_entity, start_date=pd.Timestamp(history_start).date())
        if missing:
            self.logger.warning(f"Universe tickers without entity (excluded): {missing}")
        self.ensure_factors()
        return STMTradingCycle(
            factory=factory,
            config=self.stm_config,
            history_service=history_service,
            ticker_to_entity=ordered,
            history_start=history_start,
            retrain_every_days=self.config.get("retrain_every_days", 365),
            data_updater=updater,
            universe_service=universe_setup.service,
            universe_id=getattr(universe, "id", None),
            gross_cap=self.config.get("gross_exposure_cap", 1.0),
            log=log or self.logger.info,
        )
