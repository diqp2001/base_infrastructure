"""
Portfolio optimization using Black-Litterman with ML signal integration.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from src.application.services.misbuffet.tools.optimization.portfolio.blacklitterman import BlackLittermanOptimizer
from ..config import DEFAULT_CONFIG


class HybridPortfolioOptimizer:
    """
    Portfolio optimizer combining Black-Litterman optimization with ML signals
    and spatiotemporal momentum strategies.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config['PORTFOLIO'] or DEFAULT_CONFIG['PORTFOLIO']
        self.bl_config = self.config['BLACK_LITTERMAN']
        self.risk_config = self.config['RISK_MANAGEMENT']
        
        # Initialize Black-Litterman optimizer
        #self.bl_optimizer = BlackLittermanOptimizer()
    
    def optimize_portfolio_with_signals(self,
                                      signals: Dict[str, float],
                                      returns_data: pd.DataFrame,
                                      current_date: datetime) -> Dict[str, float]:
        """
        Optimize portfolio weights using ML signals and Black-Litterman framework.
        
        Args:
            signals: Trading signals by ticker
            returns_data: Historical returns data
            current_date: Current optimization date
            
        Returns:
            Optimized portfolio weights
        """
        print(f"⚖️ Optimizing portfolio for {current_date.strftime('%Y-%m-%d')}")
        
        # Get historical returns for covariance estimation
        lookback_data = returns_data[returns_data.index <= current_date].tail(
            self.bl_config['lookback_days']
        )
        
        if len(lookback_data) < 63:  # Minimum data requirement
            return self._equal_weight_fallback(list(signals.keys()))
        
        try:
            # Step 1: Estimate covariance matrix
            covariance_matrix = self._estimate_covariance_matrix(lookback_data, signals.keys())
            
            # Step 2: Convert signals to expected returns (views)
            expected_returns = self._signals_to_expected_returns(signals, lookback_data)
            
            # Step 3: Apply Black-Litterman optimization
            optimized_weights = self._apply_black_litterman(
                expected_returns, covariance_matrix, signals.keys()
            )
            
            # Step 4: Apply risk constraints
            final_weights = self._apply_risk_constraints(optimized_weights, covariance_matrix)
            
            print(f"  ✅ Optimized weights for {len(final_weights)} assets")
            return final_weights
            
        except Exception as e:
            print(f"  ❌ Optimization failed: {str(e)}")
            return self._equal_weight_fallback(list(signals.keys()))
    
    def _estimate_covariance_matrix(self, returns_data: pd.DataFrame, tickers: List[str]) -> np.ndarray:
        """Estimate covariance matrix from historical returns."""
        # Extract returns for the specified tickers
        ticker_returns = {}
        for ticker in tickers:
            return_cols = [col for col in returns_data.columns if ticker in col and 'return' in col]
            if return_cols:
                ticker_returns[ticker] = returns_data[return_cols[0]].dropna()
        
        if not ticker_returns:
            # Fallback: create identity matrix
            return np.eye(len(tickers)) * 0.01
        
        # Create returns DataFrame
        returns_df = pd.DataFrame(ticker_returns).dropna()
        
        if len(returns_df) < 20:
            return np.eye(len(tickers)) * 0.01
        
        # Calculate covariance matrix (annualized)
        cov_matrix = returns_df.cov().values * 252
        
        # Ensure positive semi-definite
        eigenvals, eigenvecs = np.linalg.eigh(cov_matrix)
        eigenvals = np.maximum(eigenvals, 1e-8)
        cov_matrix = eigenvecs @ np.diag(eigenvals) @ eigenvecs.T
        
        return cov_matrix
    
    def _signals_to_expected_returns(self, 
                                   signals: Dict[str, float], 
                                   returns_data: pd.DataFrame) -> Dict[str, float]:
        """Convert trading signals to expected returns."""
        expected_returns = {}
        
        # Estimate market return volatility for scaling
        market_vol = self._estimate_market_volatility(returns_data)
        
        for ticker, signal in signals.items():
            # Scale signal to expected return
            # Strong signals (±1.0) should translate to ±2*market_vol annual return
            expected_return = signal * 2 * market_vol
            expected_returns[ticker] = expected_return
        
        return expected_returns
    
    def _estimate_market_volatility(self, returns_data: pd.DataFrame) -> float:
        """Estimate overall market volatility."""
        # Use average volatility across all assets
        all_returns = []
        
        for col in returns_data.columns:
            if 'return' in col:
                returns = returns_data[col].dropna()
                if len(returns) > 20:
                    all_returns.extend(returns.tolist())
        
        if not all_returns:
            return 0.15  # Default 15% volatility
        
        return np.std(all_returns) * np.sqrt(252)
    
    def _apply_black_litterman(self,
                             expected_returns: Dict[str, float],
                             covariance_matrix: np.ndarray,
                             tickers: List[str]) -> Dict[str, float]:
        """Apply Black-Litterman optimization."""
        n_assets = len(tickers)
        
        # Market cap weights (equal weight as prior)
        prior_weights = np.ones(n_assets) / n_assets
        
        # Expected returns vector
        mu = np.array([expected_returns.get(ticker, 0.0) for ticker in tickers])
        
        # Black-Litterman parameters
        tau = self.bl_config['tau']
        risk_aversion = self.bl_config['risk_aversion']
        
        # Prior returns (reverse optimization)
        prior_returns = risk_aversion * covariance_matrix @ prior_weights
        
        # Views matrix (diagonal - each asset has independent view)
        P = np.eye(n_assets)
        
        # View returns
        Q = mu
        
        # View uncertainty (diagonal matrix)
        omega = np.diag(np.diag(tau * covariance_matrix))
        
        # Black-Litterman formula
        M1 = np.linalg.inv(tau * covariance_matrix)
        M2 = P.T @ np.linalg.inv(omega) @ P
        M3 = np.linalg.inv(tau * covariance_matrix) @ prior_returns
        M4 = P.T @ np.linalg.inv(omega) @ Q
        
        # New expected returns
        mu_bl = np.linalg.inv(M1 + M2) @ (M3 + M4)
        
        # New covariance matrix
        cov_bl = np.linalg.inv(M1 + M2)
        
        # Optimal weights
        weights = np.linalg.inv(risk_aversion * cov_bl) @ mu_bl
        
        # Convert to dictionary
        weight_dict = {ticker: weight for ticker, weight in zip(tickers, weights)}
        
        return weight_dict
    
    def _apply_risk_constraints(self,
                              weights: Dict[str, float],
                              covariance_matrix: np.ndarray) -> Dict[str, float]:
        """Apply risk management constraints to portfolio weights."""
        # Apply position limits
        constrained_weights = {}
        
        min_weight = self.bl_config['min_weight']
        max_weight = self.bl_config['max_weight']
        
        for ticker, weight in weights.items():
            # Apply min/max constraints
            if weight > max_weight:
                weight = max_weight
            elif weight < min_weight and weight > 0:
                weight = min_weight
            elif weight > -min_weight and weight < 0:
                weight = -min_weight
            elif weight < -max_weight:
                weight = -max_weight
            
            constrained_weights[ticker] = weight
        
        # Normalize weights to sum to 1 (or target exposure)
        total_weight = sum(abs(w) for w in constrained_weights.values())
        target_exposure = 1.0
        
        if total_weight > 0:
            scale_factor = target_exposure / total_weight
            final_weights = {ticker: weight * scale_factor 
                           for ticker, weight in constrained_weights.items()}
        else:
            final_weights = constrained_weights
        
        return final_weights
    
    def _equal_weight_fallback(self, tickers: List[str]) -> Dict[str, float]:
        """Fallback to equal weight allocation."""
        if not tickers:
            return {}
        
        weight = 1.0 / len(tickers)
        return {ticker: weight for ticker in tickers}
    
    def calculate_portfolio_risk(self,
                               weights: Dict[str, float],
                               covariance_matrix: np.ndarray,
                               tickers: List[str]) -> Dict[str, float]:
        """Calculate portfolio risk metrics."""
        weight_array = np.array([weights.get(ticker, 0.0) for ticker in tickers])
        
        # Portfolio variance
        portfolio_variance = weight_array.T @ covariance_matrix @ weight_array
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        # Risk contribution by asset
        marginal_contrib = covariance_matrix @ weight_array
        risk_contrib = weight_array * marginal_contrib / portfolio_variance
        
        risk_metrics = {
            'portfolio_volatility': portfolio_volatility,
            'portfolio_variance': portfolio_variance,
            'risk_contributions': {ticker: contrib for ticker, contrib in zip(tickers, risk_contrib)}
        }
        
        return risk_metrics