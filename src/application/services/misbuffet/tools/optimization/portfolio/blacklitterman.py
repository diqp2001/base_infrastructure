"""
Black-Litterman Portfolio Optimizer

This module provides a simplified Black-Litterman portfolio optimization implementation
that can be used directly in trading algorithms for portfolio construction.

Author: Claude
Date: 2025-09-09
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging


class BlackLittermanOptimizer:
    """
    Simplified Black-Litterman Portfolio Optimizer.
    
    This optimizer implements the Black-Litterman model for portfolio optimization
    by combining market equilibrium assumptions with investor views.
    """
    
    def __init__(self, 
                 expected_returns: pd.Series, 
                 covariance_matrix: pd.DataFrame,
                 risk_aversion: float = 3.0,
                 tau: float = 0.025):
        """
        Initialize the Black-Litterman optimizer.
        
        Args:
            expected_returns: Series of expected returns (market equilibrium)
            covariance_matrix: Covariance matrix of returns
            risk_aversion: Risk aversion parameter (lambda)
            tau: Uncertainty parameter for the prior
        """
        self.expected_returns = expected_returns
        self.covariance_matrix = covariance_matrix
        self.risk_aversion = risk_aversion
        self.tau = tau
        
        # Views storage
        self.views = {}
        self.view_uncertainties = {}
        
        # Results storage
        self.bl_returns: Optional[pd.Series] = None
        self.bl_covariance: Optional[pd.DataFrame] = None
        self.optimal_weights: Optional[pd.Series] = None
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def add_views(self, views: Dict[str, float], confidence: float = 0.5):
        """
        Add investor views to the optimizer.
        
        Args:
            views: Dictionary mapping asset names to expected returns
            confidence: Confidence level for the views (0 to 1)
        """
        for asset, view_return in views.items():
            if asset in self.expected_returns.index:
                self.views[asset] = view_return
                # Convert confidence to uncertainty (higher confidence = lower uncertainty)
                uncertainty = self.tau * (1 - confidence)
                self.view_uncertainties[asset] = uncertainty
                self.logger.info(f"Added view for {asset}: {view_return:.4f} with uncertainty {uncertainty:.4f}")
    
    def add_relative_views(self, relative_views: Dict[Tuple[str, str], float], confidence: float = 0.5):
        """
        Add relative views between assets.
        
        Args:
            relative_views: Dictionary mapping (asset1, asset2) pairs to relative expected returns
                           (asset1 expected to outperform asset2 by this amount)
            confidence: Confidence level for the views (0 to 1)
        """
        for (asset1, asset2), relative_return in relative_views.items():
            if asset1 in self.expected_returns.index and asset2 in self.expected_returns.index:
                # Convert relative view to absolute view
                # Assume market equilibrium for both assets and add/subtract half the relative return
                base_return1 = self.expected_returns[asset1]
                base_return2 = self.expected_returns[asset2]
                
                view_return1 = base_return1 + relative_return / 2
                view_return2 = base_return2 - relative_return / 2
                
                self.add_views({asset1: view_return1, asset2: view_return2}, confidence)
    
    def solve(self) -> pd.Series:
        """
        Solve the Black-Litterman optimization problem.
        
        Returns:
            Series of optimal portfolio weights
        """
        try:
            self.logger.info("Starting Black-Litterman optimization...")
            
            # Step 1: Apply Black-Litterman if views exist
            if self.views:
                self._calculate_bl_returns_and_covariance()
                mu = self.bl_returns
                sigma = self.bl_covariance
                self.logger.info(f"Using Black-Litterman adjusted returns and covariance")
            else:
                mu = self.expected_returns
                sigma = self.covariance_matrix
                self.logger.info("No views provided - using market equilibrium")
            
            # Step 2: Mean-variance optimization
            # Optimal weights: w = (1/λ) * Σ^(-1) * μ
            sigma_inv = self._robust_inverse(sigma.values)
            optimal_weights_array = np.dot(sigma_inv, mu.values) / self.risk_aversion
            
            # Step 3: Normalize weights to sum to 1
            optimal_weights_array = optimal_weights_array / np.sum(optimal_weights_array)
            
            # Step 4: Create result series
            self.optimal_weights = pd.Series(
                optimal_weights_array, 
                index=self.expected_returns.index
            )
            
            # Step 5: Apply constraints (non-negative weights)
            self.optimal_weights = self.optimal_weights.clip(lower=0)
            
            # Step 6: Renormalize after constraints
            self.optimal_weights = self.optimal_weights / self.optimal_weights.sum()
            
            self.logger.info(f"Optimization completed. Weights: {self.optimal_weights.to_dict()}")
            return self.optimal_weights.copy()
            
        except Exception as e:
            self.logger.error(f"Error in Black-Litterman optimization: {e}")
            # Return equal weights as fallback
            n_assets = len(self.expected_returns)
            equal_weights = pd.Series(
                [1.0 / n_assets] * n_assets, 
                index=self.expected_returns.index
            )
            return equal_weights
    
    def _calculate_bl_returns_and_covariance(self):
        """
        Calculate Black-Litterman adjusted expected returns and covariance matrix.
        
        This implements the core Black-Litterman formulas:
        μ_BL = [(τΣ)^(-1) + P'Ω^(-1)P]^(-1) * [(τΣ)^(-1) * π + P'Ω^(-1) * Q]
        Σ_BL = [(τΣ)^(-1) + P'Ω^(-1)P]^(-1)
        """
        try:
            n_assets = len(self.expected_returns)
            
            # Create views matrix P (each row represents one view)
            # For simplicity, we only support direct asset views (not relative)
            P = []
            Q = []
            omega_diagonal = []
            
            for asset, view_return in self.views.items():
                # Create a row in P matrix for this view
                p_row = np.zeros(n_assets)
                asset_idx = self.expected_returns.index.get_loc(asset)
                p_row[asset_idx] = 1.0
                
                P.append(p_row)
                Q.append(view_return)
                omega_diagonal.append(self.view_uncertainties[asset])
            
            P = np.array(P)
            Q = np.array(Q)
            Omega = np.diag(omega_diagonal)
            
            # Convert to numpy arrays for calculation
            pi = self.expected_returns.values
            Sigma = self.covariance_matrix.values
            
            # Black-Litterman calculation
            tau_Sigma = self.tau * Sigma
            tau_Sigma_inv = self._robust_inverse(tau_Sigma)
            Omega_inv = self._robust_inverse(Omega)
            
            # Calculate BL expected returns
            term1 = tau_Sigma_inv + np.dot(P.T, np.dot(Omega_inv, P))
            term1_inv = self._robust_inverse(term1)
            
            term2 = np.dot(tau_Sigma_inv, pi) + np.dot(P.T, np.dot(Omega_inv, Q))
            
            mu_bl = np.dot(term1_inv, term2)
            sigma_bl = term1_inv
            
            # Store results
            self.bl_returns = pd.Series(mu_bl, index=self.expected_returns.index)
            self.bl_covariance = pd.DataFrame(sigma_bl, 
                                            index=self.covariance_matrix.index,
                                            columns=self.covariance_matrix.columns)
            
            self.logger.info("Black-Litterman returns and covariance calculated successfully")
            
        except Exception as e:
            self.logger.error(f"Error calculating Black-Litterman adjustment: {e}")
            # Fallback to original values
            self.bl_returns = self.expected_returns
            self.bl_covariance = self.covariance_matrix
    
    def _robust_inverse(self, matrix: np.ndarray, regularization: float = 1e-8) -> np.ndarray:
        """
        Compute robust matrix inverse with regularization and pseudo-inverse fallback.
        
        Args:
            matrix: Input matrix to invert
            regularization: Small value added to diagonal for regularization
            
        Returns:
            Inverse matrix
        """
        try:
            # Check condition number first
            cond_num = np.linalg.cond(matrix)
            self.logger.debug(f"Matrix condition number: {cond_num:.2e}")
            
            # If condition number is too high, use regularization
            if cond_num > 1e12:
                self.logger.warning(f"Matrix is ill-conditioned (cond={cond_num:.2e}), applying regularization")
                regularized_matrix = matrix + regularization * np.eye(matrix.shape[0])
                return np.linalg.inv(regularized_matrix)
            else:
                # Matrix is well-conditioned, use standard inverse
                return np.linalg.inv(matrix)
                
        except np.linalg.LinAlgError as e:
            # Matrix is singular, use Moore-Penrose pseudo-inverse
            self.logger.warning(f"Singular matrix detected, using pseudo-inverse: {e}")
            return np.linalg.pinv(matrix, rcond=regularization)
        except Exception as e:
            self.logger.error(f"Unexpected error in matrix inversion: {e}")
            # Last resort: return identity matrix
            return np.eye(matrix.shape[0])
    
    def get_portfolio_metrics(self) -> Dict[str, float]:
        """
        Get portfolio performance metrics.
        
        Returns:
            Dictionary with portfolio metrics
        """
        if self.optimal_weights is None:
            return {}
        
        try:
            # Expected return
            if self.bl_returns is not None:
                expected_return = np.dot(self.optimal_weights.values, self.bl_returns.values)
            else:
                expected_return = np.dot(self.optimal_weights.values, self.expected_returns.values)
            
            # Portfolio risk (volatility)
            if self.bl_covariance is not None:
                portfolio_variance = np.dot(self.optimal_weights.values, 
                                          np.dot(self.bl_covariance.values, self.optimal_weights.values))
            else:
                portfolio_variance = np.dot(self.optimal_weights.values, 
                                          np.dot(self.covariance_matrix.values, self.optimal_weights.values))
            
            portfolio_risk = np.sqrt(portfolio_variance)
            
            # Sharpe ratio (assuming risk-free rate is 0)
            sharpe_ratio = expected_return / portfolio_risk if portfolio_risk > 0 else 0
            
            return {
                'expected_return': float(expected_return),
                'portfolio_risk': float(portfolio_risk),
                'sharpe_ratio': float(sharpe_ratio),
                'num_assets': len(self.optimal_weights),
                'num_views': len(self.views),
                'max_weight': float(self.optimal_weights.max()),
                'min_weight': float(self.optimal_weights.min())
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio metrics: {e}")
            return {}