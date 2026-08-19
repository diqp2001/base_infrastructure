"""
SPX call spread algorithm — project-specific subclass.

Generic lifecycle management, portfolio tracking, performance history,
state reporting, and dependency injection live in BaseProjectAlgorithm.
Only SPX-specific logic remains here.
"""

import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Any

import pandas as pd

from src.application.managers.project_managers.market_making_SPX_call_spread_project.config import get_config
from src.application.services.misbuffet.algorithm.base_project_algorithm import BaseProjectAlgorithm

from ..strategy.market_making_strategy import Strategy
from ..strategy.risk_manager import RiskManager
from ..models.pricing_model import PricingModel
from ..models.volatility_model import VolatilityModel

logger = logging.getLogger(__name__)


class Algorithm(BaseProjectAlgorithm):
    """
    SPX call spread market making algorithm.

    Implements the SPX-specific initialize() and on_data() logic.
    All reusable helpers are inherited from BaseProjectAlgorithm.
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

        # SPX-specific components
        self.pricing_engine = None
        self.volatility_model = None

        # SPX portfolio name (resolved from config during initialize)
        self.spx_portfolio_name: Optional[str] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self):
        """SPX-specific algorithm setup, called after super().initialize()."""
        super().initialize()  # sets lookback_window, train_window, models, initialized=True

        # Load project configuration
        self.config = get_config()

        # Portfolio registration
        portfolio_config = self.config.get('Portfolio', {})
        self.spx_portfolio_name = portfolio_config.get('name', 'SPX_Call_Spread_Portfolio')

        if self._entity_service:
            portfolio_entity = self.register_portfolio(portfolio_config=portfolio_config)
            if portfolio_entity:
                self.portfolio_entity = portfolio_entity
                self.log("✅ SPX portfolio registered with EntityService system")
            else:
                self.warning("⚠️ Failed to register SPX portfolio")
        else:
            self.warning("⚠️ No EntityService available - portfolio tracking disabled")

        # Universe and data settings
        self.universe = self.config['universe']
        self.bar_size_setting = self.config['bar_size_setting']
        self.duration_str = self.config['duration_str']
        self.my_securities: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Trading logic
    # ------------------------------------------------------------------

    def on_data(self, data):
        """
        Main algorithm callback — SPX call spread market making logic.

        Args:
            data: Market data (Slice or dict) for the current bar
        """
        try:
            if not self.initialized:
                self.logger.warning("Algorithm not initialized")
                return

            # Run model training pipeline for data preparation
            if hasattr(self, 'trainer') and self.trainer:
                self.logger.info("🚀 Running model training pipeline for data preparation...")

                training_result = self.trainer.train_complete_pipeline(
                    tickers=self.universe,
                    model_type='pricing',
                    seeds=[42, 123],
                    data=data,
                )

                if training_result.get('error'):
                    self.logger.error(f"❌ Model training failed: {training_result['error']}")
                    return

                self._model_trained = True
                self.logger.info("✅ Model training pipeline completed successfully")

            # Random AAPL/MSFT allocation via UnifiedPortfolioManager → TradeManager
            random_pct = random.random()
            if self._unified_portfolio_manager:
                self._unified_portfolio_manager.set_holdings(
                    {'AAPL': random_pct, 'MSFT': 1.0 - random_pct},
                    data=data,
                )

            self._update_portfolio_value(data)
            self._update_performance_tracking(data)

            if self._is_end_of_day(data):
                self._log_daily_summary()

        except Exception as e:
            self.logger.error(f"Error in on_data: {e}")

    # ------------------------------------------------------------------
    # SPX-specific helpers
    # ------------------------------------------------------------------

    def _setup_factor_data_for_ticker(self, ticker: str, current_time: datetime) -> pd.DataFrame:
        """Set up factor-based data for a specific ticker via the factor manager."""
        try:
            self.log(f"Setting up factor data for {ticker}...")

            if hasattr(self, 'factor_manager') and self.factor_manager:
                self.log(f"Using factor manager for {ticker} data...")

                try:
                    self.factor_manager._ensure_entities_exist([ticker])
                except Exception as e:
                    self.log(f"Warning: Could not ensure entities for {ticker}: {e}")

                try:
                    factor_data = self.factor_manager.get_factor_data_for_training(
                        tickers=[ticker],
                        factor_groups=['price', 'momentum', 'technical'],
                        lookback_days=self.train_window,
                        end_date=current_time,
                    )

                    if factor_data is not None and not factor_data.empty:
                        self.log(f"Retrieved {len(factor_data)} factor data points for {ticker}")
                        df = self._convert_factor_data_to_training_format(factor_data, ticker)
                        if not df.empty:
                            return df
                    else:
                        self.log(f"No factor data available for {ticker}, falling back to basic features")
                except Exception as e:
                    self.log(f"Error getting factor data for {ticker}: {e}")

        except Exception as e:
            self.log(f"Error setting up factor data for {ticker}: {str(e)}")
            return pd.DataFrame()

    def _verify_and_import_data(self) -> Dict[str, Any]:
        """Verify SPX data exists in the DB and import via IBKR if missing."""
        try:
            if hasattr(self, 'trainer') and hasattr(self.trainer, 'database_service'):
                data_loader = self.trainer.data_loader

                data_check = data_loader.check_spx_data_availability()
                has_data = data_check.get('has_spx_data', False)

                import_results = None

                if not has_data:
                    self.logger.info("💾 Importing SPX historical data via IBKR...")
                    import_results = data_loader.import_spx_historical_data()
                    has_data = import_results.get('success', False)

                return {
                    'success': has_data,
                    'data_check': data_check,
                    'import_results': import_results,
                    'data_available': has_data,
                }
            else:
                self.logger.warning("⚠️ No database service available for data verification")
                return {'success': False, 'error': 'No database service available'}

        except Exception as e:
            self.logger.error(f"Error verifying SPX data: {e}")
            return {'success': False, 'error': str(e)}

    def _generate_new_opportunities(
        self,
        data: Dict[str, Any],
        market_analysis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate new call spread opportunities from the strategy."""
        try:
            spx_price = data.get('spx_price', 4500)

            option_chain = {
                'expiries': ['2024-01-19', '2024-01-26', '2024-02-02'],
                'strikes': list(range(int(spx_price - 100), int(spx_price + 100), 5)),
            }

            return self.strategy.generate_spread_opportunities(spx_price, option_chain, market_analysis)

        except Exception as e:
            self.logger.error(f"Error generating opportunities: {e}")
            return []

    def _evaluate_and_execute_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
        data: Dict[str, Any],
    ):
        """Evaluate and execute the top-scored spread opportunities."""
        try:
            for opportunity in opportunities[:5]:
                entry_eval = self.strategy.evaluate_spread_entry(opportunity)

                if not entry_eval.get('should_enter', False):
                    continue

                risk_check = self.risk_manager.check_position_limits(opportunity, self.positions)

                if not risk_check.get('position_approved', False):
                    self.logger.info(f"Position rejected by risk manager: {risk_check.get('violations', [])}")
                    continue

                self._execute_spread_trade(opportunity, entry_eval, data)

        except Exception as e:
            self.logger.error(f"Error evaluating and executing opportunities: {e}")

    def _execute_spread_trade(
        self,
        opportunity: Dict[str, Any],
        entry_eval: Dict[str, Any],
        data: Dict[str, Any],
    ):
        """Execute a call spread trade and record it in positions."""
        try:
            position_size = entry_eval.get('recommended_position_size', 1)

            spread_pricing = entry_eval.get('spread_pricing', {})
            max_loss = spread_pricing.get('max_loss', 0)
            required_capital = max_loss * position_size * 100  # SPX multiplier

            if required_capital > self.cash * 0.1:
                position_size = max(1, int(self.cash * 0.1 / (max_loss * 100)))

            if self.cash < required_capital:
                self.logger.warning(f"Insufficient capital: need {required_capital}, have {self.cash}")
                return

            long_option_ticket = self.market_order(
                opportunity.get('long_option_symbol', 'SPX'),
                position_size,
                tag="SPX_SPREAD_LONG",
            )
            short_option_ticket = self.market_order(
                opportunity.get('short_option_symbol', 'SPX'),
                -position_size,
                tag="SPX_SPREAD_SHORT",
            )

            position_id = f"spread_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            position = {
                'id': position_id,
                'type': opportunity.get('spread_type'),
                'strikes': {
                    'long': opportunity.get('long_strike'),
                    'short': opportunity.get('short_strike'),
                },
                'size': position_size,
                'entry_date': data.get('date', datetime.now()),
                'entry_price': spread_pricing.get('net_price', 0),
                'max_profit': spread_pricing.get('max_profit', 0),
                'max_loss': spread_pricing.get('max_loss', 0),
                'greeks': spread_pricing.get('greeks', {}),
                'underlying_price': data.get('spx_price', 4500),
                'expiry_date': opportunity.get('expiry_date'),
                'required_capital': required_capital,
                'current_value': 0,
                'long_order_id': long_option_ticket.order_id if long_option_ticket else None,
                'short_order_id': short_option_ticket.order_id if short_option_ticket else None,
            }

            self.positions[position_id] = position
            self.cash -= required_capital
            self.total_trades += 1

            self.logger.info(f"✅ Executed {position['type']} spread: {position['strikes']}, size: {position_size}")

        except Exception as e:
            self.logger.error(f"Error executing spread trade: {e}")

    def _calculate_position_value(self, position: Dict[str, Any], data: Dict[str, Any]) -> float:
        """Simplified P&L estimate for a spread position (time decay + directional factor)."""
        try:
            entry_date = position.get('entry_date', datetime.now())
            current_date = data.get('date', datetime.now())

            if isinstance(entry_date, str):
                entry_date = datetime.fromisoformat(entry_date)
            if isinstance(current_date, str):
                current_date = datetime.fromisoformat(current_date)

            days_held = (current_date - entry_date).days
            max_profit = position.get('max_profit', 0)
            max_loss = position.get('max_loss', 0)

            if position.get('type', '').startswith('bull'):
                spx_change = (data.get('spx_price', 4500) - position.get('underlying_price', 4500)) / position.get('underlying_price', 4500)
                pnl_factor = min(1, max(-1, spx_change * 5))
            else:
                spx_change = (position.get('underlying_price', 4500) - data.get('spx_price', 4500)) / position.get('underlying_price', 4500)
                pnl_factor = min(1, max(-1, spx_change * 5))

            time_decay_factor = max(0, 1 - (days_held / 30))

            if pnl_factor > 0:
                current_value = max_profit * pnl_factor * time_decay_factor
            else:
                current_value = max_loss * pnl_factor

            return current_value * position.get('size', 1)

        except Exception as e:
            self.logger.error(f"Error calculating position value: {e}")
            return 0.0
