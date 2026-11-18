"""
DispersionModelTrainer - Misbuffet BaseModelTrainer of the monthly model-filtered dispersion (same wiring as the STM
projects' STMModelTrainer).

build_cycle wires the DispersionTradingCycle onto the algorithm's own MarketDataService / MarketDataHistoryService
(frontier) and repository factory:
  * the members' CompanyShare entities and the ETF's ETFShare entity, with their daily bars (MarketDataService, IBKR
    - IBKRCompanyShareRepository / IBKRETFShareRepository; preloaded before the first bar);
  * the point-in-time Universe / UniverseConstituent rows;
  * the members IBKR no longer lists (delisted: WBA) from the file caches, same frontier rule;
  * the STM scorer (the existing STM pipeline, refit on the members, in memory), the modelled option pricer, the
    portfolio construction service and the model filter;
  * register_option: each traded leg as an option entity - the DIA calls as ETFShareOption (underlying: the ETFShare),
    the members' calls as CompanyShareOption. set_holdings keeps CompanyShareOption positions in their
    sub-portfolio; it has no ETFShareOption sub-portfolio (no ETFShareOptionPortfolio repository), so the DIA calls
    are booked directly in the main portfolio (its fallback container).
"""

import logging
import os
from datetime import date
from typing import Any, Dict

import pandas as pd

from src.application.managers.project_managers.etf_dispersion_stm_project import config as project_config
from src.application.managers.project_managers.etf_dispersion_stm_project.data.dia_universe import build_membership
from src.application.managers.project_managers.etf_dispersion_stm_project.data.price_ingestion import (
    CacheFileReader,
    DailyHistoryUpdater,
    PreferredPrices,
)
from src.application.managers.project_managers.etf_dispersion_stm_project.data.universe_setup import UniverseSetup
from src.application.services.data.backtest_preload.backtest_data_preload_service import (
    BacktestDataPreloadService,
    PreloadSeries,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_price_history import (
    STMFrontierPriceReader,
)
from src.application.services.dispersion.dispersion_portfolio_construction_service import (
    DispersionPortfolioConstructionService,
)
from src.application.services.dispersion.dispersion_trading_cycle import DispersionTradingCycle, KnownClosesReader
from src.application.services.data.entities.factor.factor_value_resolution_service import (
    FactorValueResolutionService,
)
from src.application.services.dispersion.factor_option_pricer import FactorOptionPricer, SymbolRoutedPricer
from src.application.services.dispersion.modelled_option_pricing import ModelledOptionPricer
from src.domain.entities.factor.finance.financial_assets.derivatives.option.share_option_model_price import IRX_SYMBOL
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_constituent_scorer import STMConstituentScorer
from src.application.services.misbuffet.engine.base_model_trainer import BaseModelTrainer
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.financial_assets.share.etf_share.etf_share import ETFShare

PRELOAD_FILE = "preload.csv"                       # coverage of every preloaded series (results_dir)


class DispersionModelTrainer(BaseModelTrainer):

    def __init__(self, database_service, config: Dict[str, Any]):
        super().__init__(database_service, config)
        self.stm_config = project_config.build_stm_configuration(config)
        self.logger = logging.getLogger(self.__class__.__name__)

    def preload(self, market_data_service, tickers, log=None):
        """``tickers``: [(entity class, symbol)]. BEFORE the first bar, history start .. backtest end: every member's
        and the ETF's daily TRADES bars and IBKR implied volatility (OPTION_IMPLIED_VOLATILITY: the model price's
        sigma), and the IRX index (its rate). The engine, the cycle and the option valuation then read locally.
        Coverage per series -> <results_dir>/preload.csv."""
        from src.domain.entities.finance.financial_assets.index.index import Index
        service = BacktestDataPreloadService(market_data_service, log=log or self.logger.info)
        bar = self.config["bar_size_setting"]
        series = ([PreloadSeries(cls, t, what, bar) for cls, t in tickers
                   for what in ("TRADES", "OPTION_IMPLIED_VOLATILITY")]
                  + [PreloadSeries(Index, IRX_SYMBOL, "TRADES", bar)])
        results = service.preload(series, start=self.config["price_history_start"], end=self.config["backtest_end"])
        try:
            os.makedirs(self.config["results_dir"], exist_ok=True)
            service.to_frame(results).to_csv(os.path.join(self.config["results_dir"], PRELOAD_FILE), index=False)
        except OSError as e:
            self.logger.warning(f"Could not write the preload report: {e}")
        return results

    def import_option_quotes(self, market_data_service, log):
        """ONE attempt at an option's IBKR quotes (daily MIDPOINT bars) over its life; the window is then recorded as
        covered, so the valuation never asks IBKR for it again. IBKR keeps no history of expired options: for those
        nothing comes back and the value is the model price."""
        from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import (
            CompanyShareOption,
        )
        from src.domain.entities.finance.financial_assets.derivatives.option.etf_share_option import ETFShareOption
        service = BacktestDataPreloadService(market_data_service, log=lambda m: None)

        def import_quotes(symbol: str, is_etf: bool, opened: date, expiry: date) -> None:
            cls = ETFShareOption if is_etf else CompanyShareOption
            result = service.preload([PreloadSeries(cls, symbol, "MIDPOINT", "1 day")], start=opened, end=expiry)[0]
            if result.stored_bars:
                log(f"[DISP-STM] IBKR quotes of {symbol}: {result.stored_bars} daily MIDPOINT bars")
        return import_quotes

    def file_prices(self) -> PreferredPrices:
        folder = self.config["price_history_dir"]
        return PreferredPrices([(name, CacheFileReader(os.path.join(folder, name)))
                                for name in self.config["file_price_sources"]])

    def build_cycle(self, market_data_service, history_service, factory, log=None) -> DispersionTradingCycle:
        log = log or self.logger.info
        client = getattr(getattr(market_data_service.entity_service, "repository_factory", None), "ibkr_client", None)
        connection = getattr(client, "ib_connection", None)
        if client is None or not getattr(connection, "connected_flag", False):
            raise RuntimeError("IBKR / TWS is not connected, so the members' daily bars cannot be imported.")
        membership = build_membership()
        history_start = pd.Timestamp(self.config["price_history_start"]).date()

        updater = DailyHistoryUpdater(market_data_service, membership.all_constituents(), history_start,
                                      etf=membership.etf)
        member_ids = updater.ensure_entities()                    # members IBKR lists (WBA: delisted, absent)
        etf_id = updater.ensure_etf_entity()
        if etf_id is None:
            raise RuntimeError(f"No ETFShare entity for {membership.etf} (IBKR contract lookup failed)")
        if self.config.get("preload_data", False):
            self.preload(market_data_service, [(CompanyShare, t) for t in member_ids] + [(ETFShare, membership.etf)],
                         log=log)
            updater.mark_imported()
        else:
            updater(pd.Timestamp.now())

        universe_setup = UniverseSetup(factory, membership)
        underlying_ids = {**member_ids, membership.etf: etf_id}
        universe, missing = universe_setup.register(underlying_ids)

        fallback_symbols = [s for s in membership.all_constituents() if s not in member_ids]
        if fallback_symbols:
            log(f"[DISP-STM] members IBKR does not list, closes from the file caches: {fallback_symbols}")
        reader = KnownClosesReader(
            start=history_start,
            frontier=[(STMFrontierPriceReader(history_service, frequency="1d"), member_ids),
                      (STMFrontierPriceReader(history_service, factor_type="etf_share_factor", frequency="1d"),
                       {membership.etf: etf_id})],
            fallback=self.file_prices(), fallback_symbols=fallback_symbols)

        option_repos = {True: factory.get_local_repository("ETFShareOption"),
                        False: factory.get_local_repository("CompanyShareOption")}

        def register_option(symbol: str, underlying: str, expiry: date, strike: float, multiplier: float,
                            is_etf: bool, day: date):
            repo = option_repos[bool(is_etf)]
            existing = repo.get_by_symbol(symbol)
            if existing:
                return existing
            created = repo._create_or_get(
                symbol=symbol, name=f"{underlying} {expiry} C {strike:g}", option_type="call",
                underlying_asset_id=underlying_ids[underlying], strike_price=strike, expiry=expiry.strftime("%Y%m%d"),
                multiplier=multiplier, start_date=day)
            if created is None:
                raise RuntimeError(f"Could not create the option {symbol}")
            return created

        # option prices: the factor chain the engine values the portfolio with (IBKR quote, else Black-Scholes on the
        # underlying's close, IBKR implied vol and IRX); a member IBKR does not list (no stored close, no implied
        # vol) is priced on its file-cache closes with realised volatility instead - logged, see CLAUDE.md
        factor_pricer = FactorOptionPricer(
            factory, FactorValueResolutionService(factory=factory, logger=logging.getLogger("dispersion_pricing")),
            register_option, import_quotes=self.import_option_quotes(market_data_service, log), log=log)
        pricer = SymbolRoutedPricer(factor_pricer, ModelledOptionPricer(project_config.build_option_model(self.config)),
                                    fallback_symbols=fallback_symbols, log=log)

        section = self.config["dispersion"]
        start, end = project_config.backtest_window(self.config)
        return DispersionTradingCycle(
            membership=membership,
            reader=reader,
            scorer=STMConstituentScorer(self.stm_config, section["retrain_every_rebalances"], log=log),
            pricer=pricer,
            constructor=DispersionPortfolioConstructionService(section["contracts"]),
            model_filter=project_config.build_model_filter(self.config),
            screen=project_config.build_screen(self.config),
            start=start, end=end, traded=section["traded"],
            register_option=register_option, log=log,
        )
