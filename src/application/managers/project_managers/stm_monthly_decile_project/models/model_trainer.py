"""
DecileModelTrainer - Misbuffet BaseModelTrainer of the monthly STM decile strategy (same wiring as the STM projects'
STMModelTrainer and the dispersion project's DispersionModelTrainer).

build_cycle wires the STMDecileTradingCycle onto the algorithm's MarketDataService / MarketDataHistoryService
(frontier) and repository factory:
  * the members' CompanyShare entities and daily IBKR bars (DailyHistoryUpdater, preloaded before the first bar);
  * the point-in-time Dow universe (IndexUniverseSetup: Universe / UniverseConstituent rows);
  * the closes known at each step (KnownClosesReader; a member IBKR no longer lists from the file caches): the
    research series deciles.research_price_series (ADJUSTED_LAST = dividend-adjusted, so features and decile
    returns are total returns); the engine itself trades and values at the TRADES closes;
  * model A: the existing STM pipeline on monthly rows (STMConstituentScorer);
  * model B: the same + the Eulerpool point-in-time fundamentals as extra features
    (RepositoryFactory.enable_provider_family('eulerpool') -> its statements -> CSMFundamentals: values stamped at
    publication, carried until the next filing or until stale, never a later filing).
"""

import logging
import os
from typing import Any, Dict, List

import pandas as pd

from src.application.managers.project_managers.stm_monthly_decile_project import config as project_config
from src.application.services.data.backtest_preload.backtest_data_preload_service import (
    BacktestDataPreloadService,
    PreloadSeries,
)
from src.application.services.data.backtest_preload.daily_price_sources import (
    CacheFileReader,
    DailyHistoryUpdater,
    PreferredPrices,
)
from src.application.services.data.backtest_preload.known_closes_reader import KnownClosesReader
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_constituent_scorer import (
    STMConstituentScorer,
)
from src.application.services.portfolio_research.stm_decile_cycle import (
    STMDecileTradingCycle,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_price_history import (
    STMFrontierPriceReader,
)
from src.application.services.misbuffet.engine.base_model_trainer import BaseModelTrainer
from src.application.services.universe.djia_membership import SECTORS, build_membership
from src.application.services.universe.index_universe_setup import IndexUniverseSetup
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare

PRELOAD_FILE = "preload.csv"


def fundamental_features(provider, names: List[str], log=None):
    """extra_features(dates, assets) -> {candidate: dates x assets} point-in-time values of Eulerpool's statements."""
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_fundamentals import (
        CSMFundamentals,
        statement_sources_of,
    )
    fundamentals = CSMFundamentals([statement_sources_of(provider)], names, errors=getattr(provider, "errors", ()),
                                   log=log)

    def extra(dates: pd.DatetimeIndex, assets: List[str]) -> Dict[str, pd.DataFrame]:
        return {n: fundamentals.panel(n, assets, dates) for n in names}
    extra.fundamentals = fundamentals
    return extra


class DecileModelTrainer(BaseModelTrainer):

    def __init__(self, database_service, config: Dict[str, Any]):
        super().__init__(database_service, config)
        self.stm_config = project_config.build_stm_configuration(config)
        self.logger = logging.getLogger(self.__class__.__name__)

    def price_series(self) -> List[str]:
        """IBKR whatToShow series imported for every member: TRADES (the engine's trades and valuation) and the
        research series (deciles.research_price_series) when it differs."""
        research = self.config["deciles"].get("research_price_series", "TRADES")
        return list(dict.fromkeys(["TRADES", research]))

    def preload(self, market_data_service, tickers, log=None):
        """Every member's daily bars of every price_series(), history start .. backtest end, BEFORE the first bar."""
        service = BacktestDataPreloadService(market_data_service, log=log or self.logger.info)
        series = [PreloadSeries(CompanyShare, t, what, self.config["bar_size_setting"])
                  for t in tickers for what in self.price_series()]
        results = service.preload(series, start=self.config["price_history_start"], end=self.config["backtest_end"])
        try:
            os.makedirs(self.config["results_dir"], exist_ok=True)
            service.to_frame(results).to_csv(os.path.join(self.config["results_dir"], PRELOAD_FILE), index=False)
        except OSError as e:
            self.logger.warning(f"Could not write the preload report: {e}")
        return results

    def file_prices(self) -> PreferredPrices:
        folder = self.config["price_history_dir"]
        return PreferredPrices([(name, CacheFileReader(os.path.join(folder, name)))
                                for name in self.config["file_price_sources"]])

    def scorers(self, factory, log) -> Dict[str, STMConstituentScorer]:
        section = self.config["deciles"]
        every = section["retrain_every_rebalances"]
        out = {"A": STMConstituentScorer(self.stm_config, every, log=log)}
        if "B" in project_config.variants(self.config):
            provider = factory.enable_provider_family("eulerpool")
            if provider is None:
                raise RuntimeError("model B needs the Eulerpool key (EULERPOOL_API_KEY or EULERPOOL_CREDENTIALS_FILE);"
                                   " set deciles.use_eulerpool_fundamentals = False to run model A only")
            scaling = section.get("fundamental_scaling", "sector_neutral")
            if scaling not in ("sector_neutral", "cross_sectional"):
                raise ValueError(f"deciles.fundamental_scaling must be sector_neutral or cross_sectional, got {scaling!r}")
            out["B"] = STMConstituentScorer(self.stm_config, every, log=log,
                                            extra_features=fundamental_features(provider,
                                                                                list(section["fundamentals"]), log),
                                            extra_feature_groups=SECTORS if scaling == "sector_neutral" else None)
        return out

    def build_cycle(self, market_data_service, history_service, factory, log=None) -> STMDecileTradingCycle:
        log = log or self.logger.info
        client = getattr(getattr(market_data_service.entity_service, "repository_factory", None), "ibkr_client", None)
        connection = getattr(client, "ib_connection", None)
        if client is None or not getattr(connection, "connected_flag", False):
            raise RuntimeError("IBKR / TWS is not connected, so the members' daily bars cannot be imported.")
        membership = build_membership()
        history_start = pd.Timestamp(self.config["price_history_start"]).date()
        updater = DailyHistoryUpdater(market_data_service, membership.all_constituents(), history_start)
        member_ids = updater.ensure_entities()
        if self.config.get("preload_data", False):
            self.preload(market_data_service, list(member_ids), log=log)
            updater.mark_imported()
        else:
            updater(pd.Timestamp.now())
        IndexUniverseSetup(factory, membership).register(member_ids)
        fallback_symbols = [s for s in membership.all_constituents() if s not in member_ids]
        if fallback_symbols:
            log(f"[STM-DECILE] members IBKR does not list, closes from the file caches: {fallback_symbols}")
        reader = KnownClosesReader(start=history_start,
                                   frontier=[(STMFrontierPriceReader(
                                       history_service, frequency="1d",
                                       subgroup=self.config["deciles"].get("research_price_series", "TRADES")),
                                       member_ids)],
                                   fallback=self.file_prices(), fallback_symbols=fallback_symbols)
        start, end = project_config.backtest_window(self.config)
        section = self.config["deciles"]
        return STMDecileTradingCycle(
            membership=membership, reader=reader, variants=self.scorers(factory, log),
            decile_config=project_config.build_decile_config(self.config), start=start, end=end,
            traded=section["traded_variant"], long_short_gross=section["long_short_gross"], log=log)
