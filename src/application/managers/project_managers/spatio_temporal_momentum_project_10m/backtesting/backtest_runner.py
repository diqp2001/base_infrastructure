"""
Misbuffet backtest runner for the Spatio-Temporal Momentum project
(same structure as the SPX project's runner).  The research report is built
after the run by the project manager (stm_research_report).
"""

import logging
from typing import Any, Dict


from src.application.managers.project_managers.spatio_temporal_momentum_project_10m.backtesting.base_project_algorithm import (
    Algorithm,
)
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m.models.model_trainer import (
    STMModelTrainer,
)
from src.application.services.misbuffet.engine.base_backtest_runner import BaseBacktestRunner

logger = logging.getLogger(__name__)


class BacktestRunner(BaseBacktestRunner):

    def setup_components(self, config: Dict[str, Any]) -> bool:
        try:
            self.model_trainer = STMModelTrainer(self.database_service, config)
            self.strategy = None
            return True
        except Exception as e:
            self.logger.error(f"Error setting up Spatio-Temporal Momentum components: {e}")
            return False

    def create_algorithm_instance(self) -> Algorithm:
        algorithm = Algorithm()
        # NB: BaseBacktestRunner uses `self.progress` for its own percentage (float)
        algorithm.progress_tracker = getattr(self, "progress_tracker", None)
        algorithm.set_trainer(self.model_trainer)
        algorithm.set_entity_service(self.model_trainer.data_loader.financial_asset_service)
        self.algorithm_instance = algorithm
        return algorithm
