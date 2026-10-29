"""
STMModelTrainer — Misbuffet BaseModelTrainer for the INTRADAY (10-minute) Spatio-Temporal Momentum
project (same wiring as the SPX project's ModelTrainer).

* BaseModelTrainer.create_factors creates the STM feature and signal factors
  from the factor library entries listed in config['factors'].
* build_cycle wires the time-driven STMTradingCycle onto the algorithm's
  own MarketDataService / MarketDataHistoryService (frontier).
* preload (live): the history is imported before the first decision, but registered as complete only up to the
  last bar CLOSED at that moment — bars that close later must still be requested from IBKR (a backtest registers
  up to backtest_end; live that froze every decision on the bar known at start, paper smoke run 2026-10-29).
"""

import logging
import os

import pandas as pd
from typing import Any, Dict

from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.config import (
    build_stm_configuration,
)
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.data.price_ingestion import (
    BarHistoryUpdater,
    exchange_now,
)
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.data.universe_setup import (
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

    @staticmethod
    def last_closed_bar_start(now: pd.Timestamp, bar_minutes: int) -> pd.Timestamp:
        """Start of the newest bar closed at ``now`` (10:38 -> 10:20: the 10:30 bar closes at 10:40)."""
        return pd.Timestamp(now).floor(f"{bar_minutes}min") - pd.Timedelta(minutes=bar_minutes)

    def preload(self, market_data_service, updater: BarHistoryUpdater, log=None, now=None):
        """Every 10-minute TRADES series of the universe, history start .. the last CLOSED bar, BEFORE the first
        decision (BacktestDataPreloadService): the history is then local; the bars closing during the session are
        not registered as loaded, so the engine and BarHistoryUpdater import them from IBKR as they close.
        Coverage per series -> <results_dir>/preload.csv."""
        service = BacktestDataPreloadService(market_data_service, log=log or self.logger.info)
        series = [PreloadSeries(CompanyShare, t, "TRADES", self.config["bar_size_setting"])
                  for t in updater.tickers]
        end = min(pd.Timestamp(self.config["backtest_end"]),
                  self.last_closed_bar_start(now if now is not None else exchange_now(), self.stm_config.bar_minutes))
        results = service.preload(series, start=self.config["price_history_start"], end=end)
        try:
            os.makedirs(self.config["results_dir"], exist_ok=True)
            service.to_frame(results).to_csv(os.path.join(self.config["results_dir"], PRELOAD_FILE), index=False)
        except OSError as e:
            self.logger.warning(f"Could not write the preload report: {e}")
        updater.mark_imported(through=end)            # history there up to `end`: later bars imported as they close
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
        unknown = [t for t in updater.tickers if t not in ticker_to_entity]
        if unknown:                 # IBKR has no contract for them: never request their bars (15 s timeout each)
            self.logger.warning(f"No IBKR contract / entity for {unknown}: not imported, not traded")
            updater.tickers = [t for t in updater.tickers if t in ticker_to_entity]
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
