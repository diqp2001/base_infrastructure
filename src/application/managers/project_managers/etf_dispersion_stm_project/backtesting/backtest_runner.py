"""
Misbuffet backtest runner of the monthly model-filtered dispersion (same structure as the STM projects' runner).
The A vs B report is built after the run by the project manager (dispersion_report).
"""

import logging
from typing import Any, Dict

from src.application.managers.project_managers.etf_dispersion_stm_project.backtesting.base_project_algorithm import (
    Algorithm,
)
from src.application.managers.project_managers.etf_dispersion_stm_project.models.model_trainer import (
    DispersionModelTrainer,
)
from src.application.services.misbuffet.engine.base_backtest_runner import BaseBacktestRunner

logger = logging.getLogger(__name__)


class BacktestRunner(BaseBacktestRunner):

    def setup_components(self, config: Dict[str, Any]) -> bool:
        try:
            self.model_trainer = DispersionModelTrainer(self.database_service, config)
            self.strategy = None
            return True
        except Exception as e:
            self.logger.error(f"Error setting up the dispersion components: {e}")
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
            "price_source": "TRADES",
            "include_dividends": False,
            "include_transaction_costs": False,
            "assumptions": {
                "option_prices": "IBKR MIDPOINT when quoted, else Black-Scholes (underlying close, its IBKR implied "
                                 "vol, IRX); bid = ask",
                "traded_strategy": config.get("dispersion", {}).get("traded"),
                "short_leg": "N ATM DIA calls, N fixed on the full basket", "rebalance": "monthly expiry"},
        }
