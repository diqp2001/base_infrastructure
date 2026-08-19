"""
Generic algorithm base class shared by all project-specific algorithms.

Project algorithms subclass BaseProjectAlgorithm and override:
  - initialize()   — call super() then add project-specific config/universe setup
  - on_data(data)  — all trading logic is project-specific

The methods below are fully reusable across every project and must NOT contain
any project-specific imports or logic.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from src.application.services.misbuffet.algorithm.base import QCAlgorithm


class BaseProjectAlgorithm(QCAlgorithm):
    """
    Reusable algorithm shell.

    Provides: common state initialisation, portfolio-value tracking,
    performance-history tracking, end-of-day detection, daily logging,
    unified/legacy state reporting, and all four injection setters.
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

        # Strategy / risk components — injected by BacktestRunner
        self.strategy = None
        self.risk_manager = None

        # Algorithm lifecycle flag
        self.initialized = False

        # Legacy portfolio state (used when unified portfolio manager is not active)
        self.portfolio_value: float = 0.0
        self.cash: float = 0.0
        self.positions: Dict[str, Any] = {}
        self.orders: Dict[str, Any] = {}

        # Shared config dict (populated by subclass initialize())
        self.config: Dict[str, Any] = {}
        self.database_service = None

        # Performance tracking
        self.daily_pnl: float = 0.0
        self.total_trades: int = 0
        self.performance_history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self):
        """
        Generic initialisation — sets up shared model/data attributes.

        Subclasses must call super().initialize() first, then add their own
        config loading, portfolio registration, and universe setup.
        """
        super().initialize()

        # Model / training state
        self.lookback_window: int = 20
        self.train_window: int = 252
        self.retrain_interval = timedelta(days=7)
        self.last_train_time = None

        self.models: Dict[str, Any] = {}
        self.ml_signal_generator = None

        # Data format tracking
        self._current_data_frame = None
        self._current_data_slice = None
        self._initial_training_completed = False

        self.initialized = True

    # ------------------------------------------------------------------
    # Portfolio and performance helpers
    # ------------------------------------------------------------------

    def _update_portfolio_value(self, data):
        """Refresh self.portfolio_value from the unified portfolio manager if active."""
        try:
            if self.is_unified_portfolio_enabled():
                self.portfolio_value = self.get_unified_portfolio_value()
                self.log(f"Portfolio value (unified): ${self.portfolio_value:,.2f}")
        except Exception as e:
            self.logger.error(f"Error updating portfolio value: {e}")

    def _update_performance_tracking(self, data):
        """Append a performance snapshot to self.performance_history (capped at 100 entries)."""
        try:
            total_position_value = sum(
                pos.get('current_value', 0) for pos in self.positions.values()
            )
            current_portfolio_value = self.cash + total_position_value

            if hasattr(self, 'previous_portfolio_value'):
                self.daily_pnl = current_portfolio_value - self.previous_portfolio_value
            else:
                self.daily_pnl = 0.0

            self.previous_portfolio_value = current_portfolio_value

            date = (
                data.get('date', datetime.now())
                if isinstance(data, dict)
                else getattr(data, 'time', datetime.now())
            )
            self.performance_history.append({
                'date': date,
                'portfolio_value': current_portfolio_value,
                'cash': self.cash,
                'position_value': total_position_value,
                'daily_pnl': self.daily_pnl,
                'position_count': len(self.positions),
            })
            self.performance_history = self.performance_history[-100:]

        except Exception as e:
            self.logger.error(f"Error updating performance tracking: {e}")

    def _log_daily_summary(self):
        """Emit a concise daily summary to the algorithm log."""
        try:
            self.logger.info("Daily Summary:")
            self.logger.info(f"  Portfolio Value: ${self.portfolio_value:,.2f}")
            self.logger.info(f"  Cash:            ${self.cash:,.2f}")
            self.logger.info(f"  Daily P&L:       ${self.daily_pnl:,.2f}")
            self.logger.info(f"  Active Positions: {len(self.positions)}")
            self.logger.info(f"  Total Trades:     {self.total_trades}")
        except Exception as e:
            self.logger.error(f"Error logging daily summary: {e}")

    def _is_end_of_day(self, data) -> bool:
        """Return True when the bar time is at or after 16:00 ET (simple heuristic)."""
        current_time = (
            data.get('time', datetime.now().time())
            if isinstance(data, dict)
            else getattr(data, 'time', datetime.now())
        )
        if hasattr(current_time, 'hour'):
            return current_time.hour >= 16
        return True  # default to end-of-day for daily-resolution backtests

    # ------------------------------------------------------------------
    # State reporting
    # ------------------------------------------------------------------

    def get_algorithm_state(self) -> Dict[str, Any]:
        """
        Return a unified or legacy state snapshot.

        Prefers the unified portfolio manager; falls back to the legacy
        positions/cash dict when unified PM is not active.
        """
        try:
            if self.is_unified_portfolio_enabled():
                state = self.get_unified_portfolio_state()
                state.update({
                    'initialized': self.initialized,
                    'total_trades': self.total_trades,
                    'daily_pnl': self.daily_pnl,
                    'performance_history': self.performance_history[-10:],
                    'portfolio_management': 'unified',
                    'orders_summary': self.get_unified_orders_summary(),
                    'transactions_summary': self.get_unified_transactions_summary(),
                })
                return state

            return {
                'initialized': self.initialized,
                'portfolio_value': self.portfolio_value,
                'cash': self.cash,
                'position_count': len(self.positions),
                'total_trades': self.total_trades,
                'daily_pnl': self.daily_pnl,
                'active_positions': list(self.positions.keys()),
                'performance_history': self.performance_history[-10:],
                'portfolio_management': 'legacy',
            }

        except Exception as e:
            self.logger.error(f"Error getting algorithm state: {e}")
            return {
                'error': str(e),
                'initialized': self.initialized,
                'portfolio_management': 'error',
            }

    # ------------------------------------------------------------------
    # Dependency injection setters
    # ------------------------------------------------------------------

    def set_entity_service(self, entity_service):
        """Inject EntityService and validate that all required repos are present."""
        super().set_entity_service(entity_service)

        if entity_service and entity_service.repository_factory:
            required = ['portfolio', 'order', 'transaction', 'holding']
            factory = entity_service.repository_factory
            missing = [
                r for r in required
                if not getattr(factory, f'{r}_local_repo', None)
            ]
            if missing:
                self.warning(f"Missing repositories in EntityService factory: {missing}")
            else:
                self.log("All required repositories available through EntityService")

    def set_factor_manager(self, factor_manager):
        """Inject a FactorManager from the BacktestRunner."""
        self.factor_manager = factor_manager
        self.log("Factor manager injected successfully")

    def set_trainer(self, trainer):
        """Inject a ModelTrainer from the BacktestRunner."""
        self.trainer = trainer
        self.log("Trainer injected successfully")

    def set_strategy(self, strategy):
        """Inject a Strategy from the BacktestRunner."""
        self.strategy = strategy
        self.log("Strategy injected successfully")
