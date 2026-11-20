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
from src.application.managers.project_managers.stm_monthly_decile_project.config import rebalance_labels
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

    def describe_run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """The run registry's view of this run (BaseBacktestRunner.describe_run)."""
        from src.application.services.universe.djia_membership import BASE_DATE, CHANGES, ETF, build_membership
        membership = build_membership()
        return {
            "universe_description": "Dow Jones Industrial Average members (DIA), point-in-time",
            "universe_snapshot": {
                "point_in_time_membership": True, "index": "DJIA", "etf": ETF, "base_date": str(BASE_DATE),
                "members_ever": membership.all_constituents(),
                "changes": [{"date": str(c.effective), "added": list(c.added), "removed": list(c.removed)}
                            for c in CHANGES]},
            "price_source": config["deciles"].get("research_price_series", "TRADES"),
            "include_dividends": config["deciles"].get("research_price_series") == "ADJUSTED_LAST",
            "include_transaction_costs": True,
            "gross_leverage": config["deciles"].get("long_short_gross"),
            "assumptions": {
                "engine_price_source": "TRADES", "engine_dividends": False,
                "research_price_source": config["deciles"].get("research_price_series", "TRADES"),
                "research_transaction_cost_bps": config["deciles"].get("transaction_cost_bps"),
                "engine_transaction_costs": "none (fills at the close)",
                "fundamental_scaling": config["deciles"].get("fundamental_scaling"),
                "variants": ["A", "B"] if config["deciles"].get("use_eulerpool_fundamentals") else ["A"],
                "traded_variant": config["deciles"].get("traded_variant"),
                **{k: v for k, v in rebalance_labels(config).items() if k != "token"}},
        }
