"""
Market Making Project Manager

Orchestrates derivatives market making workflows across Fixed Income,
Equity, and Commodity assets. Coordinates pricing, trading, backtesting,
and data management while delegating execution to specialized engines
and services.
"""

import os
import time
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import pandas as pd

# Base classes and services
from src.application.services.database_service.database_service import DatabaseService
from src.application.managers.project_managers.project_manager import ProjectManager

# Configuration
from .config import MarketMakingConfig, get_default_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MarketMakingProjectManager(ProjectManager):
    """
    Application-layer orchestrator for derivatives market making operations.
    
    This manager coordinates pricing, trading, backtesting, and data management
    workflows while maintaining separation between strategy intent and execution
    mechanics. It delegates to specialized engines (particularly Misbuffet) for
    actual execution.
    """
    
    def __init__(self, config: Optional[MarketMakingConfig] = None):
        """
        Initialize the Market Making Project Manager.
        
        Args:
            config: Market making configuration. Uses defaults if not provided.
        """
        super().__init__()
        
        # Configuration setup
        self.config = config or get_default_config()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize database service
        self.setup_database_service(
            DatabaseService(self.config.database.database_url)
        )
        self.database_service.set_ext_db()
        
        # Runtime state
        self.current_prices: Dict[str, Any] = {}
        self.active_quotes: Dict[str, Any] = {}
        self.portfolio_state: Dict[str, Any] = {}
        
        # Pricing and strategy components (to be initialized on demand)
        self.pricing_engines = {}
        self.strategy_engines = {}
        
        # Trading engine integration (Misbuffet)
        self.trading_engine = None
        
        self.logger.info("🏭 MarketMakingProjectManager initialized")
        self.logger.info(f"📊 Supported asset classes: {self.config.supported_asset_classes}")

    def ensure_data_ready(self, instruments: List[str]) -> Dict[str, Any]:
        """
        Ensure all required data is available before market making operations.
        
        Args:
            instruments: List of instrument identifiers
            
        Returns:
            Data availability status and any issues found
        """
        self.logger.info(f"🔍 Ensuring data readiness for {len(instruments)} instruments...")
        
        data_status = {
            'instruments_ready': [],
            'instruments_missing_data': [],
            'market_data_available': False,
            'pricing_inputs_ready': False,
            'success': False,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Check market data availability
            for instrument in instruments:
                if self._check_market_data_availability(instrument):
                    data_status['instruments_ready'].append(instrument)
                else:
                    data_status['instruments_missing_data'].append(instrument)
            
            # Check pricing inputs (curves, volatilities, etc.)
            pricing_ready = self._check_pricing_inputs()
            data_status['pricing_inputs_ready'] = pricing_ready
            
            # Overall status
            market_data_ready = len(data_status['instruments_ready']) > 0
            data_status['market_data_available'] = market_data_ready
            data_status['success'] = market_data_ready and pricing_ready
            
            if data_status['success']:
                self.logger.info("✅ All required data is ready for market making")
            else:
                self.logger.warning(f"⚠️ Data issues found: {len(data_status['instruments_missing_data'])} instruments missing data")
            
            return data_status
            
        except Exception as e:
            self.logger.error(f"❌ Error checking data readiness: {str(e)}")
            data_status['error'] = str(e)
            return data_status

    def run_pricing_cycle(self, instruments: List[str] = None) -> Dict[str, Any]:
        """
        Execute a pricing cycle for market making instruments.
        
        Args:
            instruments: List of instruments to price. Uses default universe if None.
            
        Returns:
            Pricing results and status
        """
        self.logger.info("💰 Starting pricing cycle...")
        
        if instruments is None:
            instruments = self._get_default_instrument_universe()
        
        pricing_result = {
            'instruments_priced': [],
            'pricing_errors': [],
            'total_instruments': len(instruments),
            'success': False,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Ensure data is ready
            data_status = self.ensure_data_ready(instruments)
            if not data_status['success']:
                pricing_result['error'] = "Data not ready for pricing"
                return pricing_result
            
            # Price each instrument
            for instrument in data_status['instruments_ready']:
                try:
                    prices = self._price_instrument(instrument)
                    self.current_prices[instrument] = prices
                    pricing_result['instruments_priced'].append(instrument)
                    
                except Exception as e:
                    self.logger.error(f"Error pricing {instrument}: {str(e)}")
                    pricing_result['pricing_errors'].append({
                        'instrument': instrument,
                        'error': str(e)
                    })
            
            # Update pricing result
            pricing_result['success'] = len(pricing_result['instruments_priced']) > 0
            
            if pricing_result['success']:
                self.logger.info(f"✅ Pricing cycle completed: {len(pricing_result['instruments_priced'])} instruments priced")
            else:
                self.logger.warning("⚠️ Pricing cycle completed with errors")
            
            return pricing_result
            
        except Exception as e:
            self.logger.error(f"❌ Error in pricing cycle: {str(e)}")
            pricing_result['error'] = str(e)
            return pricing_result

    def run_trading_cycle(self, instruments: List[str] = None) -> Dict[str, Any]:
        """
        Execute a trading cycle including quote generation and order management.
        
        Args:
            instruments: List of instruments to trade. Uses default universe if None.
            
        Returns:
            Trading results and status
        """
        self.logger.info("🎯 Starting trading cycle...")
        
        if instruments is None:
            instruments = list(self.current_prices.keys())
        
        trading_result = {
            'quotes_generated': [],
            'orders_submitted': [],
            'trading_errors': [],
            'total_instruments': len(instruments),
            'success': False,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Ensure we have current prices
            if not self.current_prices:
                pricing_result = self.run_pricing_cycle(instruments)
                if not pricing_result['success']:
                    trading_result['error'] = "No current prices available for trading"
                    return trading_result
            
            # Generate quotes for each instrument
            for instrument in instruments:
                if instrument in self.current_prices:
                    try:
                        quotes = self._generate_quotes(instrument)
                        self.active_quotes[instrument] = quotes
                        trading_result['quotes_generated'].append(instrument)
                        
                        # Submit orders via trading engine (Misbuffet)
                        if self.trading_engine:
                            orders = self._submit_market_making_orders(instrument, quotes)
                            trading_result['orders_submitted'].extend(orders)
                        
                    except Exception as e:
                        self.logger.error(f"Error trading {instrument}: {str(e)}")
                        trading_result['trading_errors'].append({
                            'instrument': instrument,
                            'error': str(e)
                        })
            
            # Update trading result
            trading_result['success'] = len(trading_result['quotes_generated']) > 0
            
            if trading_result['success']:
                self.logger.info(f"✅ Trading cycle completed: {len(trading_result['quotes_generated'])} instruments quoted")
            else:
                self.logger.warning("⚠️ Trading cycle completed with errors")
            
            return trading_result
            
        except Exception as e:
            self.logger.error(f"❌ Error in trading cycle: {str(e)}")
            trading_result['error'] = str(e)
            return trading_result

    def run_backtest(self, 
                    start_date: date,
                    end_date: date,
                    universe: List[str],
                    parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a backtest for the market making strategy.
        
        Args:
            start_date: Backtest start date
            end_date: Backtest end date  
            universe: List of instruments to include
            parameters: Strategy parameters
            
        Returns:
            Backtest results
        """
        self.logger.info(f"🧪 Starting backtest from {start_date} to {end_date}")
        self.logger.info(f"📈 Universe: {len(universe)} instruments")
        
        backtest_result = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'universe': universe,
            'parameters': parameters,
            'success': False,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Initialize backtest parameters
            backtest_config = self._prepare_backtest_config(
                start_date, end_date, universe, parameters
            )
            
            # Execute backtest via Misbuffet or backtesting framework
            if hasattr(self, 'backtest_runner'):
                # Use existing backtest framework
                result = self.backtest_runner.run_backtest(backtest_config)
            
            
            # Process and return results
            backtest_result.update(result)
            backtest_result['success'] = True
            
            self.logger.info("✅ Backtest completed successfully")
            return backtest_result
            
        except Exception as e:
            self.logger.error(f"❌ Error running backtest: {str(e)}")
            backtest_result['error'] = str(e)
            return backtest_result

    def get_portfolio_status(self) -> Dict[str, Any]:
        """
        Get current portfolio status including positions, P&L, and risk metrics.
        
        Returns:
            Portfolio status information
        """
        return {
            'positions': self.portfolio_state.get('positions', {}),
            'total_pnl': self.portfolio_state.get('total_pnl', Decimal('0')),
            'daily_pnl': self.portfolio_state.get('daily_pnl', Decimal('0')),
            'risk_metrics': self.portfolio_state.get('risk_metrics', {}),
            'active_quotes': len(self.active_quotes),
            'instruments_traded': list(self.active_quotes.keys()),
            'timestamp': datetime.now().isoformat()
        }

    # Private helper methods

    def _get_default_instrument_universe(self) -> List[str]:
        """Get default instrument universe for market making."""
        # This would typically come from configuration or database
        #E-mini S&P 500 Futures
        return ['ES']

    def _check_market_data_availability(self, instrument: str) -> bool:
        """Check if market data is available for an instrument."""
        # Implementation would check actual data sources
        # For now, assume data is available for known instruments
        known_instruments = self._get_default_instrument_universe()
        return instrument in known_instruments

    def _check_pricing_inputs(self) -> bool:
        """Check if pricing inputs (curves, volatilities, etc.) are ready."""
        # Implementation would verify pricing data sources
        # For now, assume inputs are ready
        return True

    def _price_instrument(self, instrument: str) -> Dict[str, Any]:
        """Price a single instrument using appropriate pricing model."""
        # This would delegate to domain pricing services
        # For now, return mock pricing data
        return {
            'mid_price': Decimal('100.0'),
            'bid_price': Decimal('99.95'),
            'ask_price': Decimal('100.05'),
            'volatility': Decimal('0.20'),
            'timestamp': datetime.now().isoformat()
        }

    def _generate_quotes(self, instrument: str) -> Dict[str, Any]:
        """Generate bid/ask quotes for market making."""
        prices = self.current_prices[instrument]
        spread = self.config.trading.bid_ask_spread_factor
        
        mid_price = prices['mid_price']
        half_spread = mid_price * spread / 2
        
        return {
            'bid_price': mid_price - half_spread,
            'ask_price': mid_price + half_spread,
            'bid_size': self.config.trading.default_quote_size,
            'ask_size': self.config.trading.default_quote_size,
            'timestamp': datetime.now().isoformat()
        }

    def _submit_market_making_orders(self, instrument: str, quotes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Submit market making orders via trading engine."""
        # This would integrate with Misbuffet trading engine
        # For now, return mock order data
        return [
            {
                'order_id': f"BID_{instrument}_{int(time.time())}",
                'side': 'BUY',
                'price': quotes['bid_price'],
                'quantity': quotes['bid_size'],
                'status': 'SUBMITTED'
            },
            {
                'order_id': f"ASK_{instrument}_{int(time.time())}",
                'side': 'SELL', 
                'price': quotes['ask_price'],
                'quantity': quotes['ask_size'],
                'status': 'SUBMITTED'
            }
        ]

    def _prepare_backtest_config(self, start_date: date, end_date: date, 
                                universe: List[str], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare configuration for backtesting."""
        return {
            'start_date': start_date,
            'end_date': end_date,
            'universe': universe,
            'initial_capital': parameters.get('initial_capital', self.config.backtest.initial_capital),
            'transaction_costs': self.config.backtest.transaction_cost_bps,
            'rebalance_frequency': self.config.backtest.rebalance_frequency,
            'strategy_parameters': parameters
        }

   