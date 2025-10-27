"""
Custom loss functions for spatiotemporal models.

Implements Sharpe ratio loss, L1 regularization, and turnover penalty
from spatiotemporal_momentum_manager.
"""

import numpy as np
import torch
import torch.nn as nn
from typing import Optional


class SpatiotemporalLossFunctions:
    """Collection of custom loss functions for spatiotemporal trading models."""
    
    @staticmethod
    def sharpe_loss(predictions: torch.Tensor, 
                   targets: torch.Tensor,
                   risk_free_rate: float = 0.02) -> torch.Tensor:
        """
        Sharpe ratio loss function.
        
        Args:
            predictions: Model predictions
            targets: Target returns
            risk_free_rate: Risk-free rate for Sharpe calculation
            
        Returns:
            Negative Sharpe ratio as loss
        """
        # Calculate portfolio returns
        portfolio_returns = predictions * targets
        
        # Calculate excess returns
        excess_returns = portfolio_returns - risk_free_rate / 252  # Daily risk-free rate
        
        # Calculate Sharpe ratio
        mean_return = torch.mean(excess_returns)
        std_return = torch.std(excess_returns)
        
        # Avoid division by zero
        sharpe_ratio = mean_return / (std_return + 1e-8)
        
        # Return negative Sharpe as loss (we want to maximize Sharpe)
        return -sharpe_ratio
    
    @staticmethod
    def reg_l1(model_params: torch.Tensor, lambda_l1: float = 0.01) -> torch.Tensor:
        """
        L1 regularization loss.
        
        Args:
            model_params: Model parameters
            lambda_l1: L1 regularization strength
            
        Returns:
            L1 regularization loss
        """
        return lambda_l1 * torch.sum(torch.abs(model_params))
    
    @staticmethod
    def reg_turnover(predictions: torch.Tensor, 
                    prev_positions: torch.Tensor,
                    lambda_turnover: float = 0.001) -> torch.Tensor:
        """
        Turnover penalty loss.
        
        Args:
            predictions: Current period predictions
            prev_positions: Previous period positions
            lambda_turnover: Turnover penalty strength
            
        Returns:
            Turnover penalty loss
        """
        # Calculate position changes (turnover)
        turnover = torch.sum(torch.abs(predictions - prev_positions))
        
        return lambda_turnover * turnover
    
    @staticmethod
    def combined_loss(predictions: torch.Tensor,
                     targets: torch.Tensor,
                     model_params: torch.Tensor,
                     prev_positions: Optional[torch.Tensor] = None,
                     weights: dict = None) -> torch.Tensor:
        """
        Combined loss function incorporating multiple objectives.
        
        Args:
            predictions: Model predictions
            targets: Target values
            model_params: Model parameters for regularization
            prev_positions: Previous positions for turnover penalty
            weights: Loss component weights
            
        Returns:
            Combined loss value
        """
        if weights is None:
            weights = {
                'mse': 0.6,
                'sharpe': 0.3,
                'l1': 0.05,
                'turnover': 0.05
            }
        
        loss = 0.0
        
        # MSE loss (base prediction accuracy)
        if weights.get('mse', 0) > 0:
            mse_loss = nn.MSELoss()(predictions, targets)
            loss += weights['mse'] * mse_loss
        
        # Sharpe ratio loss
        if weights.get('sharpe', 0) > 0:
            sharpe_loss = SpatiotemporalLossFunctions.sharpe_loss(predictions, targets)
            loss += weights['sharpe'] * sharpe_loss
        
        # L1 regularization
        if weights.get('l1', 0) > 0:
            l1_loss = SpatiotemporalLossFunctions.reg_l1(model_params, weights['l1'])
            loss += l1_loss
        
        # Turnover penalty
        if weights.get('turnover', 0) > 0 and prev_positions is not None:
            turnover_loss = SpatiotemporalLossFunctions.reg_turnover(
                predictions, prev_positions, weights['turnover']
            )
            loss += turnover_loss
        
        return loss