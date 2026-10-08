"""
Misbuffet backtest runner of the SPX call spread v2 project
(same structure as the Spatio-Temporal Momentum runners).
"""

import logging
from typing import Any, Dict

from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.backtesting.base_project_algorithm import (
    Algorithm,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.models.model_trainer import (
    MMModelTrainer,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.strategy.market_making_strategy import (
    Strategy,
)
from src.application.services.misbuffet.engine.base_backtest_runner import BaseBacktestRunner

logger = logging.getLogger(__name__)


class BacktestRunner(BaseBacktestRunner):

    def setup_components(self, config: Dict[str, Any]) -> bool:
        try:
            self.model_trainer = MMModelTrainer(self.database_service, config)
            # The engine builds its bars from the trainer's MarketDataService: give it the
            # universe name so the Universe entity is registered on the first bar.
            self.model_trainer.data_loader.market_data_service._universe_name = config['project_name']
            self.strategy = Strategy(config)
            return True
        except Exception as e:
            self.logger.error(f"Error setting up SPX call spread v2 components: {e}")
            return False

    def create_algorithm_instance(self) -> Algorithm:
        algorithm = Algorithm()
        # NB: BaseBacktestRunner uses `self.progress` for its own percentage (float)
        algorithm.progress_tracker = getattr(self, 'progress_tracker', None)
        algorithm.set_trainer(self.model_trainer)
        algorithm.set_entity_service(self.model_trainer.data_loader.financial_asset_service)
        algorithm.set_strategy(self.strategy)
        self.algorithm_instance = algorithm
        return algorithm
