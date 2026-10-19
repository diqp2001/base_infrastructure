"""
MMModelTrainer — Misbuffet BaseModelTrainer of the SPX call spread v2 project
(same role as STMModelTrainer in the Spatio-Temporal Momentum projects).

* ``ensure_factors`` creates the factors listed in config['factors']
  (BaseModelTrainer.create_factors) and returns their details;
* ``build_cycle`` wires the SPXCallSpreadTradingCycle onto the algorithm's own
  MarketDataService / MarketDataHistoryService (frontier) and repository factory.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.config import (
    get_trading_config,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.data.factor_updater import (
    FactorUpdater,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.data.position_book import (
    PositionBook,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.strategy.market_making_strategy import (
    Strategy,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.strategy.trading_cycle import (
    SPXCallSpreadTradingCycle,
)
from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import CompanyShareOption
from src.application.services.misbuffet.engine.base_model_trainer import BaseModelTrainer


class MMModelTrainer(BaseModelTrainer):

    def __init__(self, database_service, config: Dict[str, Any]):
        super().__init__(database_service, config, get_trading_config())
        self.logger = logging.getLogger(self.__class__.__name__)

    def ensure_factors(self) -> List[Dict[str, Any]]:
        """Create the factors of config['factors']; returns the factor details (factor_entity, name, ...)."""
        result = self.create_factors(self.config.get('factors', []))
        for error in result.get('errors', []):
            self.logger.warning(error)
        return result.get('factor_details', [])

    @staticmethod
    def check_ibkr_connection(market_data_service) -> None:
        factory = getattr(market_data_service.entity_service, 'repository_factory', None)
        client = getattr(factory, 'ibkr_client', None)
        connection = getattr(client, 'ib_connection', None)
        if client is None or not getattr(connection, 'connected_flag', False):
            raise RuntimeError(
                "IBKR / TWS is not connected, so no market data can be imported. Check that TWS is running "
                "on 127.0.0.1:7497 and that no other session (e.g. another project run from src/main.py) "
                "is already connected with the same client id."
            )

    def build_cycle(self, market_data_service, history_service, factory,
                    session_provider: Callable[[], Any], log=None,
                    strategy: Optional[Strategy] = None) -> SPXCallSpreadTradingCycle:
        """Entities, factors and the trading cycle, bound to the algorithm's Misbuffet services."""
        self.check_ibkr_connection(market_data_service)
        log = log or self.logger.info
        factor_groups = self.ensure_factors()
        updater = FactorUpdater(
            history_service=history_service,
            universe=self.config['universe'],
            factor_groups=factor_groups,
            bar_size_setting=self.config['bar_size_setting'],
            duration_str=self.config['duration_str'],
            log=log,
        )
        entities = updater.ensure_entities()
        log(f"SPX v2 universe: {len(entities)} entities, {len(factor_groups)} factors")
        options = self.config['universe'].get(CompanyShareOption) or []
        option_ticker = options[0] if options and isinstance(options[0], str) else None
        if option_ticker is None:
            log("No CompanyShareOption ticker in the universe: option entry disabled")
        from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.utils.data_report import (
            DataReport, run_start_checks,
        )
        report = DataReport(project=self.config.get('project_name', ''),
                            period=(str(self.config.get('backtest_start')), str(self.config.get('backtest_end'))),
                            directory=self.config.get('results_dir'))
        try:
            run_start_checks(report, self.config, factory, entities)
        except Exception as e:
            report.check(False, "start checks", f"could not run: {e}")
        return SPXCallSpreadTradingCycle(
            strategy=strategy or Strategy(self.config),
            position_book=PositionBook(factory, session_provider, report=report),
            factor_updater=updater,
            option_ticker=option_ticker,
            option_entry_weight=self.config.get('option_entry_weight', -0.2),
            hedge_symbol=self.config.get('hedge_symbol', 'SPY'),
            log=log,
        )
