"""
Hybrid spatiotemporal model wrapper combining TFT and MLP models.

Integrates the model training patterns from spatiotemporal_momentum_manager
with factor-based data inputs and signal generation capabilities.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from src.application.services.data_service.train_val_test_splitter_service import MultivariateTrainValTestSplitterService, UnivariateTrainValTestSplitterService
from src.application.services.model_service.tft_model_service import TFTModelService
from src.application.services.model_service.mlp_model_service import MLPModelService

from ..config import DEFAULT_CONFIG
from ..utils.loss_functions import SpatiotemporalLossFunctions


class HybridSpatiotemporalModel:
    """
    Hybrid model that combines TFT (Temporal Fusion Transformer) and MLP models
    for spatiotemporal momentum prediction with factor-based inputs.
    """
    
    def __init__(self, model_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the hybrid spatiotemporal model.
        
        Args:
            model_config: Configuration dictionary for model parameters
        """
        self.config = model_config or DEFAULT_CONFIG['SPATIOTEMPORAL']
        
        # Initialize model managers
        self.tft_service = TFTModelService()
        self.mlp_service = MLPModelService()
        
        # Initialize loss functions
        self.loss_functions = SpatiotemporalLossFunctions()
        
        # Model storage
        self.models = {
            'tft': {},
            'mlp': {}
        }
        
        # Training history
        self.training_history = {}
        
        # Weights directory
        self.weights_dir = Path('weights')
        self.results_dir = Path('results')
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.weights_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
    
    def train_tft_with_factors(self, 
                             splitter: MultivariateTrainValTestSplitterService,
                             start_date: datetime,
                             val_delta: timedelta,
                             test_delta: timedelta,
                             seed: int = 42) -> Dict[str, Any]:
        """
        Train TFT model using factor-enhanced data.
        
        Args:
            splitter: Multivariate data splitter with factor features
            start_date: Training start date
            val_delta: Validation period length
            test_delta: Test period length
            seed: Random seed for reproducibility
            
        Returns:
            Training results including predictions and performance metrics
        """
        print(f"🚀 Training TFT model from {start_date} (seed: {seed})")
        
        try:
            # Apply custom loss functions if configured
            model_params = self.config['TFT_PARAMS'].copy()
            if 'loss_function' in self.config:
                model_params['loss'] = self.config['loss_function']
            
            # Train using the TFT manager with custom parameters
            test_dt, val_preds, val_returns, val_vols, test_preds, test_returns, test_vols = \
                self.tft_service.train_multivariate(
                    splitter, start_date, val_delta, test_delta, seed, **model_params
                )
            
            # Store model results
            model_key = f"tft_{start_date.strftime('%Y%m%d')}_{seed}"
            self.models['tft'][model_key] = {
                'start_date': start_date,
                'test_date': test_dt,
                'seed': seed,
                'model_params': model_params
            }
            
            # Organize results
            results = {
                'model_type': 'tft',
                'model_key': model_key,
                'start_date': start_date,
                'test_date': test_dt,
                'seed': seed,
                'validation': {
                    'predictions': val_preds,
                    'returns': val_returns,
                    'volatilities': val_vols
                },
                'test': {
                    'predictions': test_preds,
                    'returns': test_returns,
                    'volatilities': test_vols
                }
            }
            
            # Calculate performance metrics
            results['performance'] = self._calculate_performance_metrics(results)
            
            print(f"  ✅ TFT training completed: {model_key}")
            return results
            
        except Exception as e:
            print(f"  ❌ TFT training failed: {str(e)}")
            return {'error': str(e), 'model_type': 'tft'}
    
    def train_mlp_with_factors(self,
                             splitter: UnivariateTrainValTestSplitterService,
                             start_date: datetime,
                             val_delta: timedelta,
                             test_delta: timedelta,
                             seed: int = 42) -> Dict[str, Any]:
        """
        Train MLP model using factor-enhanced data.
        
        Args:
            splitter: Univariate data splitter with factor features
            start_date: Training start date  
            val_delta: Validation period length
            test_delta: Test period length
            seed: Random seed for reproducibility
            
        Returns:
            Training results including predictions and performance metrics
        """
        print(f"🚀 Training MLP model from {start_date} (seed: {seed})")
        
        try:
            # Get MLP configuration
            model_params = self.config['MLP_PARAMS'].copy()
            
            # Train using the MLP manager
            test_dt, val_preds, val_returns, val_vols, test_preds, test_returns, test_vols = \
                self.mlp_service.train_univariate(
                    splitter, start_date, val_delta, test_delta, seed, **model_params
                )
            
            # Store model results
            model_key = f"mlp_{start_date.strftime('%Y%m%d')}_{seed}"
            self.models['mlp'][model_key] = {
                'start_date': start_date,
                'test_date': test_dt,
                'seed': seed,
                'model_params': model_params
            }
            
            # Organize results
            results = {
                'model_type': 'mlp',
                'model_key': model_key,
                'start_date': start_date,
                'test_date': test_dt,
                'seed': seed,
                'validation': {
                    'predictions': val_preds,
                    'returns': val_returns,
                    'volatilities': val_vols
                },
                'test': {
                    'predictions': test_preds,
                    'returns': test_returns,
                    'volatilities': test_vols
                }
            }
            
            # Calculate performance metrics
            results['performance'] = self._calculate_performance_metrics(results)
            
            print(f"  ✅ MLP training completed: {model_key}")
            return results
            
        except Exception as e:
            print(f"  ❌ MLP training failed: {str(e)}")
            return {'error': str(e), 'model_type': 'mlp'}
    
    def generate_signals_from_factors(self,
                                    factor_data: pd.DataFrame,
                                    model_type: str = 'ensemble',
                                    confidence_threshold: float = 0.6) -> pd.DataFrame:
        """
        Generate trading signals from factor data using trained models.
        
        Args:
            factor_data: DataFrame with factor features
            model_type: Type of model to use ('tft', 'mlp', 'ensemble')
            confidence_threshold: Minimum confidence for signal generation
            
        Returns:
            DataFrame with trading signals and confidence scores
        """
        print(f"📊 Generating {model_type} signals from factor data...")
        
        signals = pd.DataFrame(index=factor_data.index)
        
        if model_type == 'ensemble':
            # Combine TFT and MLP signals
            tft_signals = self._generate_model_signals(factor_data, 'tft')
            mlp_signals = self._generate_model_signals(factor_data, 'mlp')
            
            # Ensemble weighting (can be made configurable)
            tft_weight = 0.6
            mlp_weight = 0.4
            
            signals['prediction'] = (tft_signals['prediction'] * tft_weight + 
                                   mlp_signals['prediction'] * mlp_weight)
            signals['confidence'] = (tft_signals['confidence'] * tft_weight + 
                                   mlp_signals['confidence'] * mlp_weight)
        else:
            signals = self._generate_model_signals(factor_data, model_type)
        
        # Generate binary signals based on predictions and confidence
        signals['signal'] = 0
        signals.loc[(signals['prediction'] > 0) & 
                   (signals['confidence'] > confidence_threshold), 'signal'] = 1
        signals.loc[(signals['prediction'] < 0) & 
                   (signals['confidence'] > confidence_threshold), 'signal'] = -1
        
        # Add signal strength
        signals['signal_strength'] = np.abs(signals['prediction']) * signals['confidence']
        
        print(f"  ✅ Generated {len(signals)} signals")
        print(f"  📈 Long signals: {(signals['signal'] == 1).sum()}")
        print(f"  📉 Short signals: {(signals['signal'] == -1).sum()}")
        print(f"  ⏸️  Neutral signals: {(signals['signal'] == 0).sum()}")
        
        return signals
    
    def _generate_model_signals(self, factor_data: pd.DataFrame, model_type: str) -> pd.DataFrame:
        """Generate signals from a specific model type."""
        signals = pd.DataFrame(index=factor_data.index)
        signals['prediction'] = 0.0
        signals['confidence'] = 0.0
        
        # This is a placeholder - in reality, you would:
        # 1. Load trained model weights
        # 2. Prepare factor data in the format expected by the model
        # 3. Run inference to get predictions
        # 4. Convert predictions to signals
        
        # For now, create mock signals based on simple momentum
        if not factor_data.empty and 'close_price' in factor_data.columns:
            # Simple momentum-based signals as placeholder
            returns = factor_data['close_price'].pct_change()
            signals['prediction'] = returns.rolling(window=5).mean()
            signals['confidence'] = np.abs(signals['prediction']).rolling(window=5).mean()
        
        return signals
    
    def _calculate_performance_metrics(self, results: Dict[str, Any]) -> Dict[str, float]:
        """Calculate performance metrics for model results."""
        metrics = {}
        
        try:
            val_preds = results['validation']['predictions']
            val_returns = results['validation']['returns']
            test_preds = results['test']['predictions']
            test_returns = results['test']['returns']
            
            if val_preds is not None and val_returns is not None:
                # Validation metrics
                val_corr = np.corrcoef(val_preds.flatten(), val_returns.flatten())[0, 1]
                metrics['validation_correlation'] = val_corr if not np.isnan(val_corr) else 0.0
                metrics['validation_mse'] = np.mean((val_preds - val_returns) ** 2)
                metrics['validation_mae'] = np.mean(np.abs(val_preds - val_returns))
            
            if test_preds is not None and test_returns is not None:
                # Test metrics
                test_corr = np.corrcoef(test_preds.flatten(), test_returns.flatten())[0, 1]
                metrics['test_correlation'] = test_corr if not np.isnan(test_corr) else 0.0
                metrics['test_mse'] = np.mean((test_preds - test_returns) ** 2)
                metrics['test_mae'] = np.mean(np.abs(test_preds - test_returns))
            
            # Information Coefficient (IC)
            if 'test_correlation' in metrics:
                metrics['information_coefficient'] = metrics['test_correlation']
            
        except Exception as e:
            print(f"  ⚠️  Error calculating performance metrics: {str(e)}")
            metrics = {'error': str(e)}
        
        return metrics
    
    def get_model_summary(self) -> Dict[str, Any]:
        """Get summary of all trained models."""
        summary = {
            'total_models': len(self.models['tft']) + len(self.models['mlp']),
            'tft_models': len(self.models['tft']),
            'mlp_models': len(self.models['mlp']),
            'models': self.models,
            'config': self.config
        }
        
        return summary
    
    def save_model_state(self, filepath: Optional[str] = None) -> str:
        """Save the current model state."""
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = self.results_dir / f'hybrid_model_state_{timestamp}.pkl'
        
        import pickle
        
        state = {
            'models': self.models,
            'config': self.config,
            'training_history': self.training_history
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(state, f)
        
        print(f"📁 Model state saved to: {filepath}")
        return str(filepath)
    
    def load_model_state(self, filepath: str):
        """Load model state from file."""
        import pickle
        
        with open(filepath, 'rb') as f:
            state = pickle.load(f)
        
        self.models = state.get('models', {})
        self.config = state.get('config', self.config)
        self.training_history = state.get('training_history', {})
        
        print(f"📁 Model state loaded from: {filepath}")
    
    def train_rolling_window_models(self,
                                  data_splitter,
                                  date_range: List[datetime],
                                  model_type: str = 'both',
                                  seeds: List[int] = [42]) -> Dict[str, Any]:
        """
        Train models using rolling window approach from spatiotemporal_momentum_manager.
        
        Args:
            data_splitter: Prepared data splitter
            date_range: List of training start dates
            model_type: 'tft', 'mlp', or 'both'
            seeds: List of random seeds for ensemble training
            
        Returns:
            Comprehensive results dictionary
        """
        print(f"🔄 Training rolling window models: {len(date_range)} windows, {len(seeds)} seeds")
        
        all_results = {}
        val_delta = timedelta(days=self.config['TRAINING_CONFIG']['validation_delta_days'])
        test_delta = timedelta(days=self.config['TRAINING_CONFIG']['test_delta_days'])
        
        for seed in seeds:
            all_results[seed] = {}
            
            for start_date in date_range:
                dt_key = start_date.strftime('%Y-%m-%d')
                all_results[seed][dt_key] = {}
                
                # Train TFT if requested
                if model_type in ['tft', 'both']:
                    if hasattr(data_splitter, 'data') and isinstance(data_splitter, MultivariateTrainValTestSplitterService):
                        tft_results = self.train_tft_with_factors(
                            data_splitter, start_date, val_delta, test_delta, seed
                        )
                        all_results[seed][dt_key]['tft'] = tft_results
                
                # Train MLP if requested  
                if model_type in ['mlp', 'both']:
                    if hasattr(data_splitter, 'data') and isinstance(data_splitter, UnivariateTrainValTestSplitterService):
                        mlp_results = self.train_mlp_with_factors(
                            data_splitter, start_date, val_delta, test_delta, seed
                        )
                        all_results[seed][dt_key]['mlp'] = mlp_results
        
        print(f"✅ Rolling window training completed")
        
        # Store in training history
        self.training_history[datetime.now().isoformat()] = all_results
        
        return all_results