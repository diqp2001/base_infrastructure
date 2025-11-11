"""
Model training pipeline for spatiotemporal models.

Coordinates the training of TFT and MLP models with factor-enhanced data,
following the training patterns from spatiotemporal_momentum_manager.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from .spatiotemporal_model import HybridSpatiotemporalModel
from .tensor_splitter import TensorSplitterManager
from ..data.data_loader import SpatiotemporalDataLoader
from ..data.factor_manager import FactorEnginedDataManager
from ..config import DEFAULT_CONFIG


class SpatiotemporalModelTrainer:
    """
    Training pipeline manager for spatiotemporal momentum models.
    
    Orchestrates data preparation, tensor creation, and model training
    for both TFT and MLP architectures.
    """
    
    def __init__(self, database_manager):
        """
        Initialize the model trainer.
        
        Args:
            database_manager: Database manager for data access
        """
        self.database_manager = database_manager
        self.config = DEFAULT_CONFIG['SPATIOTEMPORAL']
        
        # Initialize components
        self.data_loader = SpatiotemporalDataLoader(database_manager)
        self.factor_manager = None  # Factor system removed - using CSV data directly
        self.tensor_splitter = TensorSplitterManager()
        self.model = HybridSpatiotemporalModel()
        
        # Training configuration
        self.training_config = self.config['TRAINING_CONFIG']
        self.features_config = self.config['FEATURES']
    
    def train_complete_pipeline(self,
                              tickers: Optional[List[str]] = None,
                              model_type: str = 'both',
                              seeds: List[int] = [42]) -> Dict[str, Any]:
        """
        Execute the complete training pipeline.
        
        Args:
            tickers: List of tickers to train on
            model_type: 'tft', 'mlp', or 'both'
            seeds: Random seeds for ensemble training
            
        Returns:
            Complete training results
        """
        print("🚀 Starting complete spatiotemporal training pipeline...")
        
        if tickers is None:
            tickers = DEFAULT_CONFIG['DATA']['DEFAULT_UNIVERSE']
        
        # Step 1: Prepare factor data
        print("\n📊 Step 1: Preparing factor-enhanced data...")
        factor_data = self._prepare_factor_data(tickers)
        
        # Step 2: Create training tensors
        print("\n🔧 Step 2: Creating training tensors...")
        tensor_data = self._create_training_tensors(factor_data, model_type)
        
        # Step 3: Train models
        print("\n🚀 Step 3: Training spatiotemporal models...")
        training_results = self._train_models(tensor_data, model_type, seeds)
        
        # Step 4: Evaluate performance
        print("\n📈 Step 4: Evaluating model performance...")
        performance_summary = self._evaluate_model_performance(training_results)
        
        # Compile final results
        final_results = {
            'tickers': tickers,
            'model_type': model_type,
            'seeds': seeds,
            'factor_data_summary': self._summarize_factor_data(factor_data),
            'tensor_data_summary': self._summarize_tensor_data(tensor_data),
            'training_results': training_results,
            'performance_summary': performance_summary,
            'training_completed': datetime.now().isoformat()
        }
        
        print(f"\n✅ Complete training pipeline finished!")
        print(f"   📊 Processed {len(tickers)} tickers")
        print(f"   🧠 Trained {len(seeds)} model ensembles")
        print(f"   📈 Overall performance: {performance_summary.get('overall_score', 'N/A')}")
        
        return final_results
    
    def _prepare_factor_data(self, tickers: List[str]) -> Dict[str, pd.DataFrame]:
        """Prepare factor-enhanced data for all tickers."""
        # Load historical data with factors
        historical_data = self.data_loader.load_historical_data_with_factors(tickers)
        
        # Create factor-enhanced features for each ticker
        factor_data = {}
        
        for ticker in tickers:
            # Extract ticker-specific columns
            ticker_cols = [col for col in historical_data.columns if col.startswith(f"{ticker}_")]
            if not ticker_cols:
                continue
            
            # Get ticker data
            ticker_data = historical_data[ticker_cols].copy()
            ticker_data.columns = [col.replace(f"{ticker}_", "") for col in ticker_data.columns]
            
            # Engineer features using factor manager
            from ..data.feature_engineer import SpatiotemporalFeatureEngineer
            feature_engineer = SpatiotemporalFeatureEngineer(self.database_manager)
            
            if 'close_price' in ticker_data.columns:
                enhanced_data = feature_engineer.engineer_all_features(
                    ticker_data, 'close_price'
                )
                factor_data[ticker] = enhanced_data
        
        return factor_data
    
    def _create_training_tensors(self, factor_data: Dict[str, pd.DataFrame], model_type: str) -> Dict[str, Any]:
        """Create training tensors for specified model types."""
        tensor_data = {}
        
        # Configuration from config
        feature_cols = (
            self.features_config['momentum_features'] +
            self.features_config['technical_features']
        )
        
        if model_type in ['tft', 'both']:
            # Create multivariate tensors for TFT
            print("  🔄 Creating multivariate tensors for TFT...")
            
            # Combine all ticker data for multivariate processing
            combined_data = self._combine_data_for_multivariate(factor_data)
            
            multivariate_splitter = self.tensor_splitter.create_multivariate_tensors(
                data=combined_data,
                cols=feature_cols,
                target_col='target_returns',
                timesteps=self.training_config['history_size'],
                batch_size=self.training_config['batch_size'],
                encoder_length=self.training_config['encoder_length']
            )
            
            tensor_data['multivariate'] = multivariate_splitter
        
        if model_type in ['mlp', 'both']:
            # Create univariate tensors for MLP
            print("  🔄 Creating univariate tensors for MLP...")
            
            univariate_splitter = self.tensor_splitter.create_univariate_tensors(
                data=factor_data,
                cols=feature_cols,
                target_col='target_returns',
                timesteps=21,  # Shorter history for MLP
                encoder_length=None
            )
            
            tensor_data['univariate'] = univariate_splitter
        
        return tensor_data
    
    def _train_models(self, tensor_data: Dict[str, Any], model_type: str, seeds: List[int]) -> Dict[str, Any]:
        """Train the specified model types."""
        training_results = {}
        
        # Training date range from config
        start_date_str, end_date_str = self.training_config['train_date_range']
        date_range = pd.date_range(start_date_str, end_date_str, freq='365D')
        date_range = [pd.to_datetime(d) for d in date_range]
        
        if model_type in ['tft', 'both'] and 'multivariate' in tensor_data:
            print("  🧠 Training TFT models...")
            tft_results = self.model.train_rolling_window_models(
                data_splitter=tensor_data['multivariate'],
                date_range=date_range,
                model_type='tft',
                seeds=seeds
            )
            training_results['tft'] = tft_results
        
        if model_type in ['mlp', 'both'] and 'univariate' in tensor_data:
            print("  🧠 Training MLP models...")
            mlp_results = self.model.train_rolling_window_models(
                data_splitter=tensor_data['univariate'], 
                date_range=date_range,
                model_type='mlp',
                seeds=seeds
            )
            training_results['mlp'] = mlp_results
        
        return training_results
    
    def _evaluate_model_performance(self, training_results: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate overall model performance."""
        performance_summary = {
            'models_trained': 0,
            'average_validation_correlation': 0.0,
            'average_test_correlation': 0.0,
            'best_model': None,
            'performance_details': {}
        }
        
        all_val_corrs = []
        all_test_corrs = []
        best_score = -1.0
        
        for model_type, results in training_results.items():
            model_performance = {
                'validation_correlations': [],
                'test_correlations': [],
                'model_count': 0
            }
            
            # Extract performance metrics from nested results
            for seed, seed_results in results.items():
                for date, date_results in seed_results.items():
                    if model_type in date_results:
                        model_result = date_results[model_type]
                        
                        if 'performance' in model_result:
                            perf = model_result['performance']
                            
                            if 'validation_correlation' in perf:
                                val_corr = perf['validation_correlation']
                                model_performance['validation_correlations'].append(val_corr)
                                all_val_corrs.append(val_corr)
                            
                            if 'test_correlation' in perf:
                                test_corr = perf['test_correlation']
                                model_performance['test_correlations'].append(test_corr)
                                all_test_corrs.append(test_corr)
                                
                                # Track best model
                                if test_corr > best_score:
                                    best_score = test_corr
                                    performance_summary['best_model'] = {
                                        'type': model_type,
                                        'seed': seed,
                                        'date': date,
                                        'test_correlation': test_corr
                                    }
                        
                        model_performance['model_count'] += 1
                        performance_summary['models_trained'] += 1
            
            # Calculate averages for this model type
            if model_performance['validation_correlations']:
                model_performance['avg_validation_correlation'] = np.mean(
                    model_performance['validation_correlations']
                )
            
            if model_performance['test_correlations']:
                model_performance['avg_test_correlation'] = np.mean(
                    model_performance['test_correlations']
                )
            
            performance_summary['performance_details'][model_type] = model_performance
        
        # Overall averages
        if all_val_corrs:
            performance_summary['average_validation_correlation'] = np.mean(all_val_corrs)
        
        if all_test_corrs:
            performance_summary['average_test_correlation'] = np.mean(all_test_corrs)
            # Simple overall score based on test correlation
            performance_summary['overall_score'] = np.mean(all_test_corrs)
        
        return performance_summary
    
    def _combine_data_for_multivariate(self, factor_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Combine ticker data for multivariate tensor creation."""
        combined_data = []
        
        for ticker, data in factor_data.items():
            # Add ticker column for asset identification
            data_with_ticker = data.copy()
            data_with_ticker['asset'] = ticker
            
            # Rename columns to avoid conflicts
            column_mapping = {}
            for col in data.columns:
                if col not in ['asset', 'Date']:
                    column_mapping[col] = f"{ticker}_{col}"
            
            data_with_ticker = data_with_ticker.rename(columns=column_mapping)
            combined_data.append(data_with_ticker)
        
        # Concatenate all data
        result = pd.concat(combined_data, axis=0, ignore_index=False)
        result = result.sort_index()
        
        return result
    
    def _summarize_factor_data(self, factor_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Create summary of factor data."""
        return {
            'tickers': list(factor_data.keys()),
            'total_records': sum(len(df) for df in factor_data.values()),
            'feature_columns': list(factor_data[list(factor_data.keys())[0]].columns) if factor_data else [],
            'date_range': (
                min(df.index.min() for df in factor_data.values()) if factor_data else None,
                max(df.index.max() for df in factor_data.values()) if factor_data else None
            )
        }
    
    def _summarize_tensor_data(self, tensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary of tensor data."""
        summary = {}
        
        for tensor_type, splitter in tensor_data.items():
            summary[tensor_type] = {
                'type': tensor_type,
                'splitter_class': splitter.__class__.__name__,
                'ready_for_training': True
            }
        
        return summary
    
    def save_training_results(self, results: Dict[str, Any], filepath: Optional[str] = None) -> str:
        """Save training results to file."""
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f"results/training_results_{timestamp}.pkl"
        
        import pickle
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'wb') as f:
            pickle.dump(results, f)
        
        print(f"💾 Training results saved to: {filepath}")
        return filepath
    
    def get_trained_model(self) -> HybridSpatiotemporalModel:
        """Get the trained hybrid model."""
        return self.model