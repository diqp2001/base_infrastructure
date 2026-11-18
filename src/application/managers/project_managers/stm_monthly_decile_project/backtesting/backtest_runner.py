"""
Misbuffet backtest runner of the monthly STM decile strategy (same structure as the STM projects' runner). The decile
report is built after the run by the project manager (decile_report).
"""

import logging
from typing import Any, Dict

from src.application.managers.project_managers.stm_monthly_decile_project.backtesting.base_project_algorithm import (
    Algorithm,
)
from src.application.managers.project_managers.stm_monthly_decile_project.models.model_trainer import (
    DecileModelTrainer,
)
from src.application.services.misbuffet.engine.base_backtest_runner import BaseBacktestRunner

logger = logging.getLogger(__name__)


class BacktestRunner(BaseBacktestRunner):

    def setup_components(self, config: Dict[str, Any]) -> bool:
        try:
            self.model_trainer = DecileModelTrainer(self.database_service, config)
            self.strategy = None
            return True
        except Exception as e:
            self.logger.error(f"Error setting up the decile components: {e}")
            return False

    def create_algorithm_instance(self) -> Algorithm:
        algorithm = Algorithm()
        algorithm.run_status = getattr(self, "run_status", None)
        algorithm.set_trainer(self.model_trainer)
        algorithm.set_entity_service(self.model_trainer.data_loader.financial_asset_service)
        self.algorithm_instance = algorithm
        return algorithm
