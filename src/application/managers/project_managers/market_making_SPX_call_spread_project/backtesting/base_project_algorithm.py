"""
SPX Call Spread Algorithm for Market Making

This module implements the core trading algorithm for SPX call spread market making,
integrating with the Misbuffet backtesting framework.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import pandas as pd

from application.managers.project_managers.market_making_SPX_call_spread_project.config import get_config
from application.services.misbuffet.algorithm.base import QCAlgorithm
from application.services.misbuffet.algorithm.enums import Resolution

from ..strategy.market_making_strategy import Strategy
from ..strategy.risk_manager import RiskManager
from ..models.pricing_model import PricingModel
from ..models.volatility_model import VolatilityModel

logger = logging.getLogger(__name__)


class Algorithm(QCAlgorithm):
    """
    SPX call spread market making algorithm.
    Implements systematic spread trading with risk management.
    """
    
    def __init__(self):
        """Initialize the algorithm."""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Algorithm components
        self.strategy = None
        self.risk_manager = None
        self.pricing_engine = None
        self.volatility_model = None
        
        # Algorithm state
        self.initialized = False
        self.portfolio_value = 0
        self.cash = 0
        self.positions = {}
        self.orders = {}
        
        # Configuration
        self.config = {}
        self.database_service = None
        
        # Performance tracking
        self.daily_pnl = 0
        self.total_trades = 0
        self.performance_history = []
    
    def initialize(self):
        """Initialize the algorithm following MyAlgorithm pattern."""
        # Call parent initialization first
        super().initialize()
        
        # Load configuration
        self.config = get_config()
        
        # Define universe and store Security objects
        self.universe = self.config['universe']
        self.my_securities = {}  # Dictionary to store Security objects by ticker for easy lookup
        
        """for ticker in self.universe:
            try:
                security = self.add_equity(ticker, Resolution.DAILY)
                if security is not None:
                    # Store in our custom dictionary for easy ticker-based lookup
                    self.my_securities[ticker] = security
                    self.log(f"Successfully added security: {ticker} -> {security.symbol}")
                else:
                    self.log(f"Warning: Failed to add security {ticker} - got None")
            except Exception as e:
                self.log(f"Error adding security {ticker}: {str(e)}")"""

        # Algorithm parameters
        self.lookback_window = 20   # volatility window
        self.train_window = 252     # ~1 year
        self.retrain_interval = timedelta(days=7)
        self.last_train_time = None

        # Model storage - both ML models and traditional models
        self.models = {}  # Traditional RandomForest models per ticker
        self.ml_signal_generator = None
        
        # Data tracking for flexible data format handling
        self._current_data_frame = None
        self._current_data_slice = None
        self.initialized = True
        
        # Defer initial training until dependencies are injected
        # This will be triggered by the first on_data() call or explicit training call
        self._initial_training_completed = False

    

    # ---------------------------
    # Features (Enhanced with factor system)
    # ---------------------------


   
    def _setup_factor_data_for_ticker(self, ticker: str, current_time: datetime) -> pd.DataFrame:
        """
        Set up factor-based data for a specific ticker, similar to setup_factor_system.
        
        This replaces _prepare_features() and uses the comprehensive factor system
        instead of basic technical analysis.
        """
        try:
            self.log(f"Setting up factor data for {ticker}...")
            
            # If we have a factor manager, use the comprehensive factor system
            if hasattr(self, 'factor_manager') and self.factor_manager:
                self.log(f"Using factor manager for {ticker} data...")
                
                # Ensure entity exists for this ticker
                try:
                    self.factor_manager._ensure_entities_exist([ticker])
                except Exception as e:
                    self.log(f"Warning: Could not ensure entities for {ticker}: {e}")
                
                # Get factor data for the training window
                try:
                    # Get comprehensive factor data including price, momentum, and technical factors
                    factor_data = self.factor_manager.get_factor_data_for_training(
                        tickers=[ticker],
                        factor_groups=['price', 'momentum', 'technical'],
                        lookback_days=self.train_window,
                        end_date=current_time
                    )
                    
                    if factor_data is not None and not factor_data.empty:
                        self.log(f"Retrieved {len(factor_data)} factor data points for {ticker}")
                        
                        # Convert factor data to the format expected by the model
                        df = self._convert_factor_data_to_training_format(factor_data, ticker)
                        if not df.empty:
                            return df
                    else:
                        self.log(f"No factor data available for {ticker}, falling back to basic features")
                except Exception as e:
                    self.log(f"Error getting factor data for {ticker}: {e}")
                
            
            
        except Exception as e:
            self.log(f"Error setting up factor data for {ticker}: {str(e)}")
            # Return empty DataFrame to trigger fallback logic
            return pd.DataFrame()
    
    def on_data(self, data: Dict[str, Any]):
        """
        Main algorithm logic called on each data update.
        Enhanced to include data stage functionality and model training integration.
        
        Args:
            data: Market data dictionary containing date/time and basic market info
        """
        try:
            if not self.initialized:
                self.logger.warning("Algorithm not initialized")
                return
            
            
            
            # Step 1: Execute model training pipeline for data creation and verification
            if hasattr(self, 'trainer') and self.trainer and not hasattr(self, '_model_trained'):
                self.logger.info("🚀 Running model training pipeline for data preparation...")
                training_result = self.trainer.train_complete_pipeline(
                    tickers=self.universe,
                    model_type='pricing',  # Use pricing models for SPX options
                    seeds=[42, 123]
                )
                
                if training_result.get('error'):
                    self.logger.error(f"❌ Model training failed: {training_result['error']}")
                    return
                
                self._model_trained = True
                self.logger.info("✅ Model training pipeline completed successfully")
            
            # ============================
            # MARKET MAKING LOGIC
            # ============================
            # Update portfolio tracking
            self._update_portfolio_value(data)
            
            # Analyze market conditions using available data
            market_analysis = {}
            if hasattr(self, 'strategy') and self.strategy:
                market_analysis = self.strategy.analyze_market_conditions(data)
            
            # Manage existing positions
            if hasattr(self, 'strategy') and self.strategy:
                position_management = self.strategy.manage_existing_positions()
            
            # Generate new opportunities if we have capacity
            max_positions = getattr(self, 'max_positions', 10)
            if len(self.positions) < max_positions:
                opportunities = self._generate_new_opportunities(data, market_analysis)
                self._evaluate_and_execute_opportunities(opportunities, data)
            
            # Update performance tracking
            self._update_performance_tracking(data)
            
            # Log daily summary
            if self._is_end_of_day(data):
                self._log_daily_summary()
            
        except Exception as e:
            self.logger.error(f"Error in on_data: {e}")
    
    def _verify_and_import_data(self) -> Dict[str, Any]:
        """
        Verify SPX data exists and import if necessary.
        Moved from ProjectManager._run_data_stage()
        """
        try:
            
            
            if hasattr(self, 'trainer') and hasattr(self.trainer, 'database_service'):
                data_loader = self.trainer.data_loader
                
                # Check data availability
                data_check = data_loader.check_spx_data_availability()
                has_data = data_check.get('has_spx_data', False)
                
                import_results = None
                
                # Import data if missing
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
    
    def _update_portfolio_value(self, data: Dict[str, Any]):
        """Update portfolio value based on current market data."""
        try:
            # Calculate position values
            total_position_value = 0
            
            for position_id, position in self.positions.items():
                position_value = self._calculate_position_value(position, data)
                position['current_value'] = position_value
                total_position_value += position_value
            
            # Update portfolio value
            self.portfolio_value = self.cash + total_position_value
            
        except Exception as e:
            self.logger.error(f"Error updating portfolio value: {e}")
    
    def _generate_new_opportunities(
        self,
        data: Dict[str, Any],
        market_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate new spread opportunities."""
        try:
            spx_price = data.get('spx_price', 4500)
            
            # Mock option chain data (in practice, this would come from market data)
            option_chain = {
                'expiries': ['2024-01-19', '2024-01-26', '2024-02-02'],
                'strikes': list(range(int(spx_price - 100), int(spx_price + 100), 5)),
            }
            
            # Generate spread opportunities
            opportunities = self.strategy.generate_spread_opportunities(
                spx_price, option_chain, market_analysis
            )
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error generating opportunities: {e}")
            return []
    
    def _evaluate_and_execute_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
        data: Dict[str, Any]
    ):
        """Evaluate and execute promising opportunities."""
        try:
            for opportunity in opportunities[:5]:  # Limit to top 5
                # Evaluate entry criteria
                entry_eval = self.strategy.evaluate_spread_entry(opportunity)
                
                if not entry_eval.get('should_enter', False):
                    continue
                
                # Check risk limits
                risk_check = self.risk_manager.check_position_limits(
                    opportunity, self.positions
                )
                
                if not risk_check.get('position_approved', False):
                    self.logger.info(f"Position rejected by risk manager: {risk_check.get('violations', [])}")
                    continue
                
                # Execute the trade
                self._execute_spread_trade(opportunity, entry_eval, data)
                
        except Exception as e:
            self.logger.error(f"Error evaluating and executing opportunities: {e}")
    
    def _execute_spread_trade(
        self,
        opportunity: Dict[str, Any],
        entry_eval: Dict[str, Any],
        data: Dict[str, Any]
    ):
        """Execute a spread trade."""
        try:
            # Calculate position size
            position_size = entry_eval.get('recommended_position_size', 1)
            
            # Calculate required capital
            spread_pricing = entry_eval.get('spread_pricing', {})
            max_loss = spread_pricing.get('max_loss', 0)
            required_capital = max_loss * position_size * 100  # SPX multiplier
            
            if required_capital > self.cash * 0.1:  # Limit to 10% of cash per trade
                position_size = max(1, int(self.cash * 0.1 / (max_loss * 100)))
            
            if self.cash < required_capital:
                self.logger.warning(f"Insufficient capital for trade: need {required_capital}, have {self.cash}")
                return
            
            # Create position record
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
            }
            
            # Add position to portfolio
            self.positions[position_id] = position
            self.cash -= required_capital
            self.total_trades += 1
            
            self.logger.info(f"✅ Executed {position['type']} spread: {position['strikes']}, size: {position_size}")
            
        except Exception as e:
            self.logger.error(f"Error executing spread trade: {e}")
    
    def _calculate_position_value(self, position: Dict[str, Any], data: Dict[str, Any]) -> float:
        """Calculate current value of a position."""
        try:
            # In a real implementation, this would use current option prices
            # For now, use a simplified approach
            
            entry_date = position.get('entry_date', datetime.now())
            current_date = data.get('date', datetime.now())
            
            if isinstance(entry_date, str):
                entry_date = datetime.fromisoformat(entry_date)
            if isinstance(current_date, str):
                current_date = datetime.fromisoformat(current_date)
            
            # Simple time decay calculation
            days_held = (current_date - entry_date).days
            max_profit = position.get('max_profit', 0)
            max_loss = position.get('max_loss', 0)
            
            # Simplified P&L calculation (would use real option pricing in practice)
            if position.get('type', '').startswith('bull'):
                # Bull spread - profits if underlying rises
                spx_change = (data.get('spx_price', 4500) - position.get('underlying_price', 4500)) / position.get('underlying_price', 4500)
                pnl_factor = min(1, max(-1, spx_change * 5))  # Scale factor
            else:
                # Bear spread - profits if underlying falls
                spx_change = (position.get('underlying_price', 4500) - data.get('spx_price', 4500)) / position.get('underlying_price', 4500)
                pnl_factor = min(1, max(-1, spx_change * 5))  # Scale factor
            
            # Add time decay effect
            time_decay_factor = max(0, 1 - (days_held / 30))  # Decay over 30 days
            
            if pnl_factor > 0:
                current_value = max_profit * pnl_factor * time_decay_factor
            else:
                current_value = max_loss * pnl_factor
            
            return current_value * position.get('size', 1)
            
        except Exception as e:
            self.logger.error(f"Error calculating position value: {e}")
            return 0
    
    def _update_performance_tracking(self, data: Dict[str, Any]):
        """Update performance tracking metrics."""
        try:
            # Calculate daily P&L
            total_position_value = sum(pos.get('current_value', 0) for pos in self.positions.values())
            current_portfolio_value = self.cash + total_position_value
            
            if hasattr(self, 'previous_portfolio_value'):
                self.daily_pnl = current_portfolio_value - self.previous_portfolio_value
            else:
                self.daily_pnl = 0
            
            self.previous_portfolio_value = current_portfolio_value
            
            # Update performance history
            self.performance_history.append({
                'date': data.get('date', datetime.now()),
                'portfolio_value': current_portfolio_value,
                'cash': self.cash,
                'position_value': total_position_value,
                'daily_pnl': self.daily_pnl,
                'position_count': len(self.positions),
            })
            
            # Keep only last 100 days of history
            self.performance_history = self.performance_history[-100:]
            
        except Exception as e:
            self.logger.error(f"Error updating performance tracking: {e}")
    
    def _is_end_of_day(self, data: Dict[str, Any]) -> bool:
        """Check if this is end of trading day."""
        # Simple check - in practice, this would be more sophisticated
        current_time = data.get('time', datetime.now().time())
        if hasattr(current_time, 'hour'):
            return current_time.hour >= 16  # 4 PM ET
        return True  # Default to end of day for daily backtests
    
    def _log_daily_summary(self):
        """Log daily performance summary."""
        try:
            self.logger.info(f"📊 Daily Summary:")
            self.logger.info(f"   Portfolio Value: ${self.portfolio_value:,.2f}")
            self.logger.info(f"   Cash: ${self.cash:,.2f}")
            self.logger.info(f"   Daily P&L: ${self.daily_pnl:,.2f}")
            self.logger.info(f"   Active Positions: {len(self.positions)}")
            self.logger.info(f"   Total Trades: {self.total_trades}")
            
        except Exception as e:
            self.logger.error(f"Error logging daily summary: {e}")
    
    def get_algorithm_state(self) -> Dict[str, Any]:
        """Get current algorithm state."""
        try:
            return {
                'initialized': self.initialized,
                'portfolio_value': self.portfolio_value,
                'cash': self.cash,
                'position_count': len(self.positions),
                'total_trades': self.total_trades,
                'daily_pnl': self.daily_pnl,
                'active_positions': list(self.positions.keys()),
                'performance_history': self.performance_history[-10:],  # Last 10 days
            }
            
        except Exception as e:
            self.logger.error(f"Error getting algorithm state: {e}")
            return {
                'error': str(e),
                'initialized': self.initialized,
            }
        
        # Event handlers are inherited from QCAlgorithm base class
    
    def set_factor_manager(self, factor_manager):
        """Inject factor manager from the BacktestRunner."""
        self.factor_manager = factor_manager
        self.log("✅ Factor manager injected successfully")
        
    
    def set_trainer(self, trainer):
        """Inject  trainer from the BacktestRunner."""
        self.trainer = trainer
        self.log("✅  trainer injected successfully")
    
    def set_strategy(self, strategy):
        """Inject momentum strategy from the BacktestRunner."""
        self.strategy = strategy
        self.log("✅ Momentum strategy injected successfully")
    