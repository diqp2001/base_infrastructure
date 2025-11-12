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
        self.factor_manager = FactorEnginedDataManager(database_manager)  # Use factor system for database-driven approach
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
        
        # Step 1: Prepare factor data (store in database, don't create tensors)
        print("\n📊 Step 1: Preparing factor-enhanced data...")
        factor_data = self._prepare_factor_data(tickers)
        
        # Step 2: Create training tensors (separate step as requested)
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
            'training_completed': datetime.now().isoformat(),
            'factors_stored_in_database': True  # Indicating database-driven approach
        }
        
        print(f"\n✅ Complete training pipeline finished!")
        print(f"   📊 Processed {len(tickers)} tickers")
        print(f"   🧠 Trained {len(seeds)} model ensembles")
        print(f"   📈 Overall performance: {performance_summary.get('overall_score', 'N/A')}")
        
        return final_results
    
    def _ensure_factors_exist(self, tickers: List[str], overwrite: bool = False) -> None:
        """Ensure all factors exist in database, following backtestRunner pattern."""
        print("  📍 Ensuring factor system is populated...")
        
        # Replicate the backtestRunner setup process
        # 1. Ensure basic entities exist
        entities_summary = self.factor_manager._ensure_entities_exist(tickers)
        
        # 2. Populate price factors  
        price_summary = self.factor_manager.populate_price_factors(tickers, overwrite)
        
        # 3. Populate momentum factors
        momentum_summary = self.factor_manager.populate_momentum_factors(tickers, overwrite)
        
        # 4. Calculate technical indicators
        technical_summary = self.factor_manager.calculate_technical_indicators(tickers, overwrite)
        
        # 5. Create volatility and target factors (NEW)
        volatility_summary = self._populate_volatility_factors(tickers, overwrite)

        target_summary = self._populate_target_factors(tickers, overwrite)
        
        print(f"  ✅ Factor system populated:")
        print(f"    • Price: {price_summary.get('values_calculated', 0)} values")
        print(f"    • Momentum: {momentum_summary.get('values_calculated', 0)} values")
        print(f"    • Technical: {technical_summary.get('values_calculated', 0)} values")
        print(f"    • Volatility: {volatility_summary.get('values_calculated', 0)} values")
        print(f"    • Targets: {target_summary.get('values_calculated', 0)} values")
        
    def _populate_volatility_factors(self, tickers: List[str], overwrite: bool = False) -> Dict[str, Any]:
        """Populate volatility factors using new domain classes."""
        from domain.entities.factor.finance.financial_assets.share_factor.volatility_factor_share_value import ShareVolatilityFactorValue
        from domain.entities.factor.finance.financial_assets.share_factor.volatility_factor_share import ShareVolatilityFactor
        
        print("📊 Populating volatility factors...")
        
        volatility_factors = [
            {'name': 'daily_vol', 'volatility_type': 'daily_vol', 'period': 21},
            {'name': 'monthly_vol', 'volatility_type': 'monthly_vol', 'period': 63},
            {'name': 'vol_of_vol', 'volatility_type': 'vol_of_vol', 'period': 21},
            {'name': 'realized_vol', 'volatility_type': 'realized_vol', 'period': 21}
        ]
        
        total_values = 0
        
        for vol_config in volatility_factors:
            # Create or get factor definition
            factor = self.factor_manager.share_factor_repository.get_by_name(vol_config['name'])
            if not factor:
                factor = self.factor_manager.share_factor_repository.add_factor(
                    name=vol_config['name'],
                    factor_type='volatility',
                    description=f"Volatility factor: {vol_config['volatility_type']} (period: {vol_config['period']})"
                )
                
            
            # Calculate and store values for each ticker
            for ticker in tickers:
                share = self.factor_manager.company_share_repository.get_by_ticker(ticker)
                if share:
                    share = share[0] if isinstance(share, list) else share
                    
                    # Load price data
                    ticker_data = self._load_ticker_price_data(ticker)
                    if ticker_data is not None and not ticker_data.empty:
                        
                        # Create domain entity and calculate values
                        volatility_entity = ShareVolatilityFactor(
                            name=vol_config['name'],
                            factor_type='volatility',
                            description=f"Volatility: {vol_config['volatility_type']}",
                            volatility_type=vol_config['volatility_type'],
                            period=vol_config['period']
                        )
                        
                        vol_calculator = ShareVolatilityFactorValue(self.database_manager, volatility_entity)
                        
                        values_stored = vol_calculator.store_factor_values(
                            repository=self.factor_manager.share_factor_repository,
                            factor=factor,
                            share=share,
                            data=ticker_data,
                            column_name='close_price',
                            volatility_type=vol_config['volatility_type'],
                            period=vol_config['period'],
                            overwrite=overwrite
                        )
                        
                        total_values += values_stored
                        print(f"  ✅ {ticker}: stored {values_stored} {vol_config['name']} values")
        
        return {'values_calculated': total_values, 'factors_created': len(volatility_factors)}
    
    def _populate_target_factors(self, tickers: List[str], overwrite: bool = False) -> Dict[str, Any]:
        """Populate target variable factors using new domain classes."""
        from domain.entities.factor.finance.financial_assets.share_factor.target_factor_share_value import ShareTargetFactorValue
        from domain.entities.factor.finance.financial_assets.share_factor.target_factor_share import ShareTargetFactor
        
        print("🎯 Populating target factors...")
        
        target_factors = [
            {'name': 'target_returns', 'target_type': 'target_returns', 'forecast_horizon': 1, 'is_scaled': True},
            {'name': 'target_returns_nonscaled', 'target_type': 'target_returns_nonscaled', 'forecast_horizon': 1, 'is_scaled': False}
        ]
        
        total_values = 0
        
        for target_config in target_factors:
            # Create or get factor definition
            factor = self.factor_manager.share_factor_repository.get_by_name(target_config['name'])
            
            if not factor:
                factor = self.factor_manager.share_factor_repository.add_factor(
                    name=target_config['name'],
                    factor_type='target',
                    description=f"Target variable: {target_config['target_type']} (horizon: {target_config['forecast_horizon']})"
                )
            
            # Calculate and store values for each ticker
            for ticker in tickers:
                share = self.factor_manager.company_share_repository.get_by_ticker(ticker)
                if share:
                    share = share[0] if isinstance(share, list) else share
                    
                    # Load price data
                    ticker_data = self._load_ticker_price_data(ticker)
                    if ticker_data is not None and not ticker_data.empty:
                        
                        # Create domain entity and calculate values
                        target_entity = ShareTargetFactor(
                            name=target_config['name'],
                            factor_type='target',
                            description=f"Target: {target_config['target_type']}",
                            target_type=target_config['target_type'],
                            forecast_horizon=target_config['forecast_horizon'],
                            is_scaled=target_config['is_scaled']
                        )
                        
                        target_calculator = ShareTargetFactorValue(self.database_manager, target_entity)
                        
                        values_stored = target_calculator.store_factor_values(
                            repository=self.factor_manager.share_factor_repository,
                            factor=factor,
                            share=share,
                            data=ticker_data,
                            column_name='close_price',
                            target_type=target_config['target_type'],
                            forecast_horizon=target_config['forecast_horizon'],
                            is_scaled=target_config['is_scaled'],
                            overwrite=overwrite
                        )
                        
                        total_values += values_stored
                        print(f"  ✅ {ticker}: stored {values_stored} {target_config['name']} values")
        
        return {'values_calculated': total_values, 'factors_created': len(target_factors)}
    
    def _load_ticker_factor_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """Load all factor data for a single ticker from database."""
        try:
            # Use factor manager's method to load comprehensive factor data
            factor_groups = ['price', 'momentum', 'technical', 'volatility', 'target']
            ticker_data = self.factor_manager._get_ticker_factor_data(
                ticker=ticker,
                start_date=None,  # Use default date range
                end_date=None,
                factor_groups=factor_groups
            )
            
            return ticker_data
            
        except Exception as e:
            print(f"  ⚠️  Error loading factor data for {ticker}: {str(e)}")
            return None
    
    def _load_ticker_price_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """Load price data for a single ticker from CSV files."""
        try:
            csv_file = self.factor_manager.stock_data_path / f"{ticker}_stock_data.csv"
            if csv_file.exists():
                data = pd.read_csv(csv_file, index_col=0, parse_dates=True)
                return data
            else:
                print(f"  ⚠️  CSV file not found for {ticker}: {csv_file}")
                return None
                
        except Exception as e:
            print(f"  ⚠️  Error loading price data for {ticker}: {str(e)}")
            return None
    
    def _prepare_factor_data(self, tickers: List[str]) -> Dict[str, pd.DataFrame]:
        """Prepare factor-enhanced data for all tickers using database-driven approach."""
        print(f"📊 Preparing factor data using database for {len(tickers)} tickers...")
        
        # Step 1: Ensure all factors exist in database (like backtestRunner)
        self._ensure_factors_exist(tickers, overwrite=False)
        
        # Step 2: Load factor data from database for each ticker
        factor_data = {}
        
        for ticker in tickers:
            print(f"  🔍 Loading factor data for {ticker}...")
            ticker_data = self._load_ticker_factor_data(ticker)
            
            if ticker_data is not None and not ticker_data.empty:
                factor_data[ticker] = ticker_data
                print(f"    ✅ Loaded {len(ticker_data)} records with {len(ticker_data.columns)} factors")
            else:
                print(f"    ⚠️  No factor data found for {ticker}")
        
        print(f"✅ Factor data preparation complete: {len(factor_data)} tickers processed")
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