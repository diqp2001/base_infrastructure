"""
Black-Litterman Portfolio Optimization Framework Algorithm

This module implements the Black-Litterman portfolio optimization model,
which combines market equilibrium assumptions with investor views to generate
optimal portfolio allocations.

The Black-Litterman model:
1. Starts with market capitalization weights as the equilibrium portfolio
2. Calculates implied equilibrium returns
3. Incorporates investor views through a views matrix
4. Optimizes portfolio weights using the adjusted expected returns

Author: Claude
Date: 2025-07-08
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging

# Update imports to use relative paths to common modules
try:
    from ...common.interfaces import IAlgorithm
    from ...common.symbol import Symbol
    from ...common.enums import Resolution, SecurityType
    from ...common.data_types import Slice
except ImportError:
    # Fallback imports for standalone testing
    from ..algorithm.base import QCAlgorithm as IAlgorithm
    from ..algorithm.symbol import Symbol
    from ..algorithm.enums import Resolution, SecurityType
    from ..algorithm.data_handlers import Slice


class BlackLittermanPortfolioOptimizationAlgorithm(IAlgorithm):
    """
    Black-Litterman Portfolio Optimization Framework Algorithm
    
    This algorithm implements the Black-Litterman model for portfolio optimization:
    
    1. Universe Selection: Select a universe of assets (equities)
    2. Market Cap Weights: Use market capitalization as equilibrium weights
    3. Implied Returns: Calculate implied equilibrium returns
    4. Views Integration: Incorporate investor views about expected returns
    5. Portfolio Optimization: Generate optimal portfolio weights
    6. Rebalancing: Periodically rebalance the portfolio
    
    The algorithm follows the QuantConnect framework structure and can be used
    for both backtesting and live trading.
    """
    
    def __init__(self):
        """Initialize the Black-Litterman Portfolio Optimization Algorithm."""
        # Initialize the parent interface
        if hasattr(super(), '__init__'):
            super().__init__()
        
        # Algorithm parameters
        self.universe_size = 10  # Number of assets in universe
        self.rebalance_frequency = 30  # Rebalance every 30 days
        self.lookback_period = 252  # 1 year of data for covariance estimation
        self.risk_aversion = 3.0  # Risk aversion parameter (lambda)
        self.tau = 0.025  # Black-Litterman uncertainty parameter
        
        # Data storage
        self.price_history: Dict[str, List[float]] = {}
        self.returns_history: Dict[str, List[float]] = {}
        self.market_caps: Dict[str, float] = {}
        
        # Portfolio state
        self.current_weights: Dict[str, float] = {}
        self.target_weights: Dict[str, float] = {}
        self.last_rebalance_date: Optional[datetime] = None
        self.equilibrium_weights: Dict[str, float] = {}
        self.implied_returns: Dict[str, float] = {}
        
        # Views and confidence
        self.views_matrix: Optional[np.ndarray] = None
        self.view_values: Optional[np.ndarray] = None
        self.omega_matrix: Optional[np.ndarray] = None
        
        # Universe symbols
        self.universe_symbols: List[Symbol] = []
        self.symbol_names: List[str] = []
        
        # Performance tracking
        self.rebalance_count = 0
        self.optimization_history: List[Dict] = []
        
        # Logging
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Black-Litterman Portfolio Optimization Algorithm initialized")
    
    def initialize(self):
        """
        Initialize the Black-Litterman algorithm.
        
        This method:
        1. Sets up the universe of assets
        2. Configures rebalancing schedule
        3. Initializes data structures
        4. Sets initial portfolio parameters
        """
        # Define universe of assets (major US equities)
        universe_tickers = [
            "SPY",   # SPDR S&P 500 ETF
            "QQQ",   # Invesco QQQ ETF
            "IWM",   # iShares Russell 2000 ETF
            "VTI",   # Vanguard Total Stock Market ETF
            "AAPL",  # Apple Inc.
            "MSFT",  # Microsoft Corporation
            "GOOGL", # Alphabet Inc.
            "AMZN",  # Amazon.com Inc.
            "TSLA",  # Tesla Inc.
            "NVDA"   # NVIDIA Corporation
        ]
        
        # Initialize data structures for each symbol
        for ticker in universe_tickers[:self.universe_size]:
            try:
                # Create symbol object
                symbol = Symbol(ticker)
                self.universe_symbols.append(symbol)
                self.symbol_names.append(ticker)
                
                # Initialize data structures
                self.price_history[ticker] = []
                self.returns_history[ticker] = []
                self.current_weights[ticker] = 0.0
                self.target_weights[ticker] = 0.0
                self.market_caps[ticker] = 1.0  # Will be updated with real data
                
                self.logger.info(f"Added {ticker} to universe")
                
            except Exception as e:
                self.logger.error(f"Failed to add {ticker}: {e}")
        
        # Initialize equilibrium weights (equal-weighted as starting point)
        equal_weight = 1.0 / len(self.symbol_names)
        for ticker in self.symbol_names:
            self.equilibrium_weights[ticker] = equal_weight
        
        self.logger.info(f"Initialized universe with {len(self.universe_symbols)} assets")
        self.logger.info("Black-Litterman algorithm initialization complete")
    
    def on_data(self, data):
        """
        Process new market data.
        
        Args:
            data: Market data slice containing prices for all securities
        """
        # Handle both Slice objects and dictionary data
        if hasattr(data, 'bars'):
            self._process_data_slice(data)
        else:
            # Handle dictionary data (for compatibility)
            self._process_dict_data(data)
    
    def _process_data_slice(self, data):
        """
        Process data in Slice format.
        
        Args:
            data: Slice object containing market data
        """
        try:
            # Update price history for each symbol
            for symbol in self.universe_symbols:
                ticker = symbol.value
                if symbol in data.bars:
                    bar = data.bars[symbol]
                    price = float(bar.close)
                    
                    if price > 0:
                        self._update_symbol_data(ticker, price)
            
            # Check if it's time to rebalance
            if self._should_rebalance():
                self.rebalance_portfolio()
                
        except Exception as e:
            self.logger.error(f"Error processing data slice: {e}")
    
    def _process_dict_data(self, data):
        """
        Process data in dictionary format.
        
        Args:
            data: Dictionary containing market data
        """
        try:
            # Handle simple dictionary format
            if isinstance(data, dict):
                for ticker in self.symbol_names:
                    if ticker in data:
                        price_data = data[ticker]
                        if isinstance(price_data, dict):
                            price = float(price_data.get('close', price_data.get('value', 0)))
                        else:
                            price = float(price_data)
                        
                        if price > 0:
                            self._update_symbol_data(ticker, price)
            
            # Check if it's time to rebalance
            if self._should_rebalance():
                self.rebalance_portfolio()
                
        except Exception as e:
            self.logger.error(f"Error processing dictionary data: {e}")
    
    def _update_symbol_data(self, ticker: str, price: float):
        """
        Update price and return data for a symbol.
        
        Args:
            ticker: Symbol ticker
            price: Current price
        """
        try:
            # Add new price
            self.price_history[ticker].append(price)
            
            # Calculate return
            if len(self.price_history[ticker]) > 1:
                prev_price = self.price_history[ticker][-2]
                return_val = (price - prev_price) / prev_price
                self.returns_history[ticker].append(return_val)
            
            # Maintain rolling window
            if len(self.price_history[ticker]) > self.lookback_period:
                self.price_history[ticker].pop(0)
                self.returns_history[ticker].pop(0)
                
        except Exception as e:
            self.logger.error(f"Error updating data for {ticker}: {e}")
    
    def _should_rebalance(self) -> bool:
        """
        Check if portfolio should be rebalanced.
        
        Returns:
            True if rebalancing is needed
        """
        if self.last_rebalance_date is None:
            return True
        
        # For simulation, use a simple counter-based approach
        return len(self.price_history.get(self.symbol_names[0], [])) % self.rebalance_frequency == 0
    
    def rebalance_portfolio(self):
        """
        Rebalance the portfolio using Black-Litterman optimization.
        
        This method:
        1. Estimates market equilibrium weights
        2. Calculates covariance matrix
        3. Derives implied equilibrium returns
        4. Incorporates investor views
        5. Optimizes portfolio weights
        6. Executes trades to achieve target weights
        """
        try:
            self.logger.info("Starting portfolio rebalancing...")
            
            # Step 1: Ensure we have sufficient data
            if not self._has_sufficient_data():
                self.logger.info("Insufficient data for optimization")
                return
            
            # Step 2: Calculate market equilibrium weights
            self._calculate_market_cap_weights()
            
            # Step 3: Estimate covariance matrix
            covariance_matrix = self._calculate_covariance_matrix()
            if covariance_matrix is None:
                self.logger.error("Failed to calculate covariance matrix")
                return
            
            # Step 4: Calculate implied equilibrium returns
            self._calculate_implied_returns(covariance_matrix)
            
            # Step 5: Set up investor views
            self._setup_investor_views()
            
            # Step 6: Apply Black-Litterman optimization
            optimal_weights = self._black_litterman_optimization(covariance_matrix)
            
            if optimal_weights is not None:
                # Step 7: Update target weights (simulation mode)
                self.target_weights = optimal_weights.copy()
                self.current_weights = optimal_weights.copy()
                self.last_rebalance_date = datetime.now()
                self.rebalance_count += 1
                
                self.logger.info(f"Portfolio rebalancing complete (#{self.rebalance_count})")
                self.logger.info(f"New weights: {optimal_weights}")
            else:
                self.logger.error("Black-Litterman optimization failed")
                
        except Exception as e:
            self.logger.error(f"Error during portfolio rebalancing: {e}")
    
    def _has_sufficient_data(self) -> bool:
        """
        Check if we have sufficient historical data for optimization.
        
        Returns:
            True if sufficient data is available
        """
        min_required_points = 60  # Minimum 60 data points
        
        for ticker in self.symbol_names:
            if len(self.returns_history.get(ticker, [])) < min_required_points:
                return False
        
        return True
    
    def _calculate_market_cap_weights(self):
        """
        Calculate market capitalization weights for equilibrium portfolio.
        
        In a real implementation, this would use actual market cap data.
        For this example, we'll use a simplified approach based on price levels.
        """
        try:
            # Simplified market cap proxy using average prices
            avg_prices = {}
            total_market_value = 0.0
            
            for ticker in self.symbol_names:
                if self.price_history.get(ticker):
                    avg_price = np.mean(self.price_history[ticker][-30:])  # 30-day average
                    # Assume equal number of shares outstanding (simplified)
                    market_value = avg_price * 1000000  # Arbitrary share count
                    avg_prices[ticker] = market_value
                    total_market_value += market_value
            
            # Calculate weights
            for ticker in self.symbol_names:
                if total_market_value > 0:
                    self.equilibrium_weights[ticker] = avg_prices.get(ticker, 0) / total_market_value
                else:
                    self.equilibrium_weights[ticker] = 1.0 / len(self.symbol_names)
            
            self.logger.info(f"Market cap weights calculated: {self.equilibrium_weights}")
            
        except Exception as e:
            self.logger.error(f"Error calculating market cap weights: {e}")
            # Fallback to equal weights
            equal_weight = 1.0 / len(self.symbol_names)
            for ticker in self.symbol_names:
                self.equilibrium_weights[ticker] = equal_weight
    
    def _calculate_covariance_matrix(self) -> Optional[np.ndarray]:
        """
        Calculate the covariance matrix of asset returns.
        
        Returns:
            Covariance matrix as numpy array, or None if calculation fails
        """
        try:
            # Prepare returns data
            returns_data = []
            min_length = min(len(self.returns_history.get(ticker, [])) for ticker in self.symbol_names)
            
            if min_length < 30:  # Minimum 30 observations
                return None
            
            # Create aligned returns matrix
            for ticker in self.symbol_names:
                returns_data.append(self.returns_history[ticker][-min_length:])
            
            # Convert to numpy array and calculate covariance
            returns_matrix = np.array(returns_data).T  # Transpose for proper orientation
            covariance_matrix = np.cov(returns_matrix.T) * 252  # Annualized
            
            self.logger.info(f"Covariance matrix calculated: {covariance_matrix.shape}")
            return covariance_matrix
            
        except Exception as e:
            self.logger.error(f"Error calculating covariance matrix: {e}")
            return None
    
    def _calculate_implied_returns(self, covariance_matrix: np.ndarray):
        """
        Calculate implied equilibrium returns using the Black-Litterman model.
        
        Formula: π = λ * Σ * w
        where:
        - π = implied returns
        - λ = risk aversion parameter
        - Σ = covariance matrix
        - w = market equilibrium weights
        
        Args:
            covariance_matrix: Asset covariance matrix
        """
        try:
            # Convert equilibrium weights to numpy array
            weights_array = np.array([self.equilibrium_weights[ticker] for ticker in self.symbol_names])
            
            # Calculate implied returns: π = λ * Σ * w
            implied_returns_array = self.risk_aversion * np.dot(covariance_matrix, weights_array)
            
            # Store as dictionary
            for i, ticker in enumerate(self.symbol_names):
                self.implied_returns[ticker] = float(implied_returns_array[i])
            
            self.logger.info(f"Implied returns calculated: {self.implied_returns}")
            
        except Exception as e:
            self.logger.error(f"Error calculating implied returns: {e}")
    
    def _setup_investor_views(self):
        """
        Set up investor views for the Black-Litterman model.
        
        This method defines:
        1. Views matrix (P) - which assets the views relate to
        2. View values (Q) - the expected returns based on views
        3. Confidence matrix (Omega) - uncertainty about the views
        
        For this example, we'll create simple momentum-based views.
        """
        try:
            num_assets = len(self.symbol_names)
            
            # Example views based on recent momentum
            views = []
            view_values = []
            
            # View 1: Technology stocks (AAPL, MSFT, GOOGL) will outperform by 2%
            if all(ticker in self.symbol_names for ticker in ['AAPL', 'MSFT', 'GOOGL']):
                tech_view = np.zeros(num_assets)
                for i, ticker in enumerate(self.symbol_names):
                    if ticker in ['AAPL', 'MSFT', 'GOOGL']:
                        tech_view[i] = 1/3  # Equal weight among tech stocks
                    elif ticker in ['SPY', 'QQQ']:
                        tech_view[i] = -1/2  # Relative to broad market
                
                views.append(tech_view)
                view_values.append(0.02)  # 2% outperformance
            
            # View 2: Small caps (IWM) will underperform large caps (SPY) by 1%
            if 'IWM' in self.symbol_names and 'SPY' in self.symbol_names:
                size_view = np.zeros(num_assets)
                iwm_idx = self.symbol_names.index('IWM')
                spy_idx = self.symbol_names.index('SPY')
                size_view[iwm_idx] = 1
                size_view[spy_idx] = -1
                
                views.append(size_view)
                view_values.append(-0.01)  # 1% underperformance
            
            # Convert to numpy arrays
            if views:
                self.views_matrix = np.array(views)
                self.view_values = np.array(view_values)
                
                # Create diagonal confidence matrix (tau * P * Sigma * P')
                # Simplified: use identity matrix scaled by tau
                num_views = len(views)
                self.omega_matrix = np.eye(num_views) * self.tau
                
                self.logger.info(f"Set up {num_views} investor views")
            else:
                self.logger.info("No views set up - using market equilibrium only")
                
        except Exception as e:
            self.logger.error(f"Error setting up investor views: {e}")
    
    def _black_litterman_optimization(self, covariance_matrix: np.ndarray) -> Optional[Dict[str, float]]:
        """
        Perform Black-Litterman portfolio optimization.
        
        The Black-Litterman formula:
        μ_BL = [(τΣ)^(-1) + P'Ω^(-1)P]^(-1) * [(τΣ)^(-1) * π + P'Ω^(-1) * Q]
        Σ_BL = [(τΣ)^(-1) + P'Ω^(-1)P]^(-1)
        
        Then optimize: w* = (λΣ_BL)^(-1) * μ_BL
        
        Args:
            covariance_matrix: Asset covariance matrix
            
        Returns:
            Dictionary of optimal portfolio weights
        """
        try:
            num_assets = len(self.symbol_names)
            
            # Convert implied returns to array
            pi_array = np.array([self.implied_returns[ticker] for ticker in self.symbol_names])
            
            # Calculate tau * Sigma
            tau_sigma = self.tau * covariance_matrix
            tau_sigma_inv = np.linalg.inv(tau_sigma)
            
            if self.views_matrix is not None and self.view_values is not None:
                # With views: Black-Litterman formula
                P = self.views_matrix
                Q = self.view_values
                Omega = self.omega_matrix
                Omega_inv = np.linalg.inv(Omega)
                
                # Calculate BL expected returns
                term1 = tau_sigma_inv + np.dot(P.T, np.dot(Omega_inv, P))
                term1_inv = np.linalg.inv(term1)
                
                term2 = np.dot(tau_sigma_inv, pi_array) + np.dot(P.T, np.dot(Omega_inv, Q))
                
                mu_bl = np.dot(term1_inv, term2)
                sigma_bl = term1_inv
                
                self.logger.info("Applied Black-Litterman with views")
            else:
                # Without views: use equilibrium returns
                mu_bl = pi_array
                sigma_bl = covariance_matrix
                
                self.logger.info("Applied equilibrium optimization (no views)")
            
            # Optimize portfolio weights: w* = (λ * Σ_BL)^(-1) * μ_BL
            lambda_sigma_bl = self.risk_aversion * sigma_bl
            lambda_sigma_bl_inv = np.linalg.inv(lambda_sigma_bl)
            
            optimal_weights_array = np.dot(lambda_sigma_bl_inv, mu_bl)
            
            # Normalize weights to sum to 1
            optimal_weights_array = optimal_weights_array / np.sum(optimal_weights_array)
            
            # Convert to dictionary
            optimal_weights = {}
            for i, ticker in enumerate(self.symbol_names):
                optimal_weights[ticker] = float(optimal_weights_array[i])
            
            # Ensure non-negative weights (simple constraint)
            for ticker in optimal_weights:
                optimal_weights[ticker] = max(0.0, optimal_weights[ticker])
            
            # Renormalize after applying constraints
            total_weight = sum(optimal_weights.values())
            if total_weight > 0:
                for ticker in optimal_weights:
                    optimal_weights[ticker] /= total_weight
            
            self.logger.info(f"Optimal weights calculated: {optimal_weights}")
            
            # Store optimization results
            optimization_result = {
                'timestamp': datetime.now(),
                'optimal_weights': optimal_weights.copy(),
                'expected_returns': {ticker: float(mu_bl[i]) for i, ticker in enumerate(self.symbol_names)},
                'risk_aversion': self.risk_aversion,
                'num_views': len(self.views_matrix) if self.views_matrix is not None else 0
            }
            self.optimization_history.append(optimization_result)
            
            return optimal_weights
            
        except Exception as e:
            self.logger.error(f"Error in Black-Litterman optimization: {e}")
            return None
    
    def on_order_event(self, order_event):
        """
        Handle order events.
        
        Args:
            order_event: Order event details
        """
        self.logger.info(f"Order event: {order_event}")
    
    def get_optimization_history(self) -> List[Dict]:
        """
        Get the history of optimization results.
        
        Returns:
            List of optimization result dictionaries
        """
        return self.optimization_history.copy()
    
    def get_current_weights(self) -> Dict[str, float]:
        """
        Get current portfolio weights.
        
        Returns:
            Dictionary of current portfolio weights
        """
        return self.current_weights.copy()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get algorithm performance summary.
        
        Returns:
            Dictionary with performance metrics
        """
        return {
            'total_rebalances': self.rebalance_count,
            'current_portfolio_value': 1000000.0,  # Simplified for demo
            'initial_capital': 1000000.0,
            'total_return': 0.0,  # Would be calculated from portfolio performance
            'current_weights': self.get_current_weights(),
            'optimization_count': len(self.optimization_history),
            'algorithm_type': 'BlackLitterman_Portfolio_Optimization'
        }