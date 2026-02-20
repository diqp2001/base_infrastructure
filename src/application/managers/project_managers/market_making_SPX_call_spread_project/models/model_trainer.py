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

from application.managers.project_managers.market_making_SPX_call_spread_project.models.pricing_model import PricingModel
from src.domain.entities.factor.factor import Factor
from src.dto.factor.factor_batch import FactorBatch

from ..data.data_loader import DataLoader
from ..data.factor_manager import FactorManager
from ..data.factor_normalizer import FactorNormalizer
from ..config import DEFAULT_CONFIG, get_config, get_trading_config


class ModelTrainer:
    """
    Training pipeline manager 
    
    
    """
    
    def __init__(self, database_service):
        """
        Initialize the model trainer.
        
        Args:
            database_service: Database manager for data access
        """
        self.database_service = database_service
        self.config = get_config()
        
        # Initialize components
        self.data_loader = DataLoader(database_service)
        self.factor_manager = FactorManager(database_service)  # Use factor system for database-driven approach
        self.factor_normalizer = FactorNormalizer(database_service)  # NEW: Factor normalization component
        
        # Training configuration
        self.training_config = get_trading_config()
        self.features_config = self.config
    
    def train_complete_pipeline(self,
                              tickers: Optional[List[str]] = None,
                              model_type: str = 'both',
                              seeds: Optional[List[int]] = None,data=None) -> Dict[str, Any]:
        """
        Execute the complete training pipeline.
        
        Args:
            tickers: List of tickers to train on
            model_type: 'tft', 'mlp', 'both', or 'pricing'
            seeds: Random seeds for ensemble training
            
        Returns:
            Complete training results
        """
        print("🚀 Starting complete spatiotemporal training pipeline...")
        
        # if tickers is None:
        #     tickers = DEFAULT_CONFIG['DATA']['DEFAULT_UNIVERSE']
        
        if seeds is None:
            seeds = [42, 123]
        date = list(data.items())[0][1].time #date from data
        # Step 1: Prepare factor data (store in database, don't create tensors)
        print("\n📊 Step 1: Preparing factor-enhanced data...")
        factor_data = self._prepare_factor_data(date)
        
        # Step 2: NEW - Apply comprehensive normalization and factor enhancement
        print("\n🔧 Step 2: Normalizing and enhancing factors...")
        normalized_factor_data = self._normalize_and_enhance_factors(factor_data)
        
        # Step 3: Create training tensors (separate step as requested)
        print("\n🔧 Step 3: Creating training tensors...")
        tensor_data = self._create_training_tensors(normalized_factor_data, model_type)
        
        # Step 4: Train models
        print("\n🚀 Step 4: Training spatiotemporal models...")
        training_results = self._train_models(tensor_data, model_type)
        
        # Step 5: Evaluate performance
        print("\n📈 Step 5: Evaluating model performance...")
        performance_summary = self._evaluate_model_performance(training_results)
        
        # Compile final results
        final_results = {
            'tickers': tickers,
            'model_type': model_type,
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
    
    def _ensure_factors_exist(self) -> None:
        """
        Create factor domain entities from config using factor_batch DTO for optimized batch operations.
        
        Args:
            tickers: List of tickers to create factors for
            overwrite: Whether to overwrite existing factors
            
        Returns:
            Dict containing factor creation summary
        """
        # factors_config = self.config.get('factors', {})
        results = {
            'factors_created': 0,
            'factors_skipped': 0,
            'target_factors_created': 0,
            'return_factors_created': 0,
            'return_factor_dependencies': 0,
            'factor_details': [],
            'return_factor_details': [],
            'errors': [],
            'factor_batches': []
        }
        
        try:
            
            
            # Create factors from config using the new create_factors method
            factors_config = self.config.get('factors', [])
            if factors_config:
                factor_results = self.create_factors(factors_config)
                results['config_factors_created'] = factor_results['factors_created']
                results['config_factor_details'] = factor_results['factor_details']
                print(f"    🔗 Created {factor_results['factors_created']} factors from config")
            
            # Create target factors for specified tickers
            # target_config = self.config.get('target_factor', {})
            # if target_config:
            #     results['target_factors_created'] = self._create_target_factors(
            #         target_config, tickers, overwrite
            #     )
            
            print(f"✅ Factor population complete: {results['factors_created']} batch factors created in {len(results['factor_batches'])} batches, {results.get('config_factors_created', 0)} config factors created, {results['factors_skipped']} skipped")
            return results
            
        except Exception as e:
            error_msg = f"Error in populate_factors: {str(e)}"
            results['errors'].append(error_msg)
            print(f"❌ {error_msg}")
            return results
        
        
        
        
 
    
    def create_factors(self, factors_config: List[Dict]) -> Dict[str, Any]:
        """
        Create factors from config file using factor definitions.
        
        Args:
            factors_config: List of factor configurations from config file
            tickers: List of tickers to associate with factors
            
        Returns:
            Dictionary containing factor creation results
        """
        results = {
            'factors_created': 0,
            'factor_details': [],
            'errors': []
        }
        
        try:
            for factor_config in factors_config:
                if not isinstance(factor_config, dict):
                    continue
                    
                factor_name = factor_config.get('name')
                if not factor_name:
                    continue
                    
                try:
                    # Create factor entity using MarketDataHistoryService
                    factor_creation_config = {
                        'entity_class': factor_config.get('class', 'unknown'),
                        'name': factor_name,
                        'entity_symbol': factor_name,
                        'group': factor_config.get('group', 'unknown'),
                        'subgroup': factor_config.get('subgroup', 'default'),
                        'data_type': factor_config.get('data_type', 'numeric'),
                        'source': 'config',
                        'definition': factor_config.get('definition', f'Factor {factor_name} from config'),
                        'factor_index': results['factors_created'],
                        'factor_future_start': datetime.now()
                    }
                    
                    # Create or get factor using market data history service
                    if hasattr(self.data_loader, 'market_data_history_service'):
                        factor_entity = self.data_loader.market_data_history_service._create_or_get(factor_creation_config)
                    
                    
                    if factor_entity:
                        results['factors_created'] += 1
                        results['factor_details'].append({
                            'factor_entity':factor_entity,
                            'name': factor_name,
                            'group': factor_config.get('group', 'unknown'),
                            'subgroup': factor_config.get('subgroup', 'default'),
                            'status': 'created'
                        })
                        print(f"    ✅ Created factor: {factor_name}")
                    else:
                        error_msg = f"Failed to create factor {factor_name}"
                        results['errors'].append(error_msg)
                        print(f"    ❌ {error_msg}")
                        
                except Exception as e:
                    error_msg = f"Error creating factor {factor_name}: {str(e)}"
                    results['errors'].append(error_msg)
                    print(f"    ❌ {error_msg}")
            
            return results
            
        except Exception as e:
            error_msg = f"Error in create_factors: {str(e)}"
            results['errors'].append(error_msg)
            print(f"❌ {error_msg}")
            return results
    
    def _create_price_dependencies_for_return_factor(self, return_factor: Any, symbol: str, 
                                                   asset_class: type, price_factor_names: List[str]) -> int:
        """
        Create FactorDependency relationships between return factor and price factors.
        
        Args:
            return_factor: The return factor that depends on price factors
            symbol: Symbol for the asset (e.g., SPX, ES)
            asset_class: Asset class (Index or IndexFuture)
            price_factor_names: List of price factor names (open, high, low, close)
            
        Returns:
            Number of dependencies created
        """
        from src.domain.entities.factor.factor_dependency import FactorDependency
        
        dependencies_created = 0
        
        try:
            for price_factor_name in price_factor_names:
                try:
                    # Create price factor config for MarketDataHistoryService
                    price_factor_config = {
                        'entity_class': type(return_factor),  # Use same class as return factor for consistency
                        'entity_symbol': f"{symbol}_{price_factor_name}",
                        'name': f"{symbol}_{price_factor_name}",
                        'group': 'price',
                        'subgroup': 'ohlc',
                        'data_type': 'numeric',
                        'source': 'market_data',
                        'definition': f'{price_factor_name.title()} price factor for {symbol}',
                        'underlying_symbol': symbol
                    }
                    
                    # Get or create price factor using MarketDataHistoryService
                    price_factor = self.data_loader.market_data_history_service._create_or_get(price_factor_config)
                    
                    if price_factor and hasattr(return_factor, 'id') and hasattr(price_factor, 'id'):
                        # Create dependency relationship
                        dependency = FactorDependency(
                            dependent_factor_id=return_factor.id,
                            independent_factor_id=price_factor.id,
                            dependency_type='calculation',
                            description=f'{return_factor.name} depends on {price_factor.name} for return calculation'
                        )
                        
                        # TODO: Persist dependency using appropriate repository
                        # For now, just count it as created
                        dependencies_created += 1
                        print(f"      🔗 Created dependency: {return_factor.name} -> {price_factor.name}")
                    
                except Exception as e:
                    print(f"      ❌ Error creating dependency for {price_factor_name}: {str(e)}")
                    continue
            
            return dependencies_created
            
        except Exception as e:
            print(f"❌ Error in _create_price_dependencies_for_return_factor: {str(e)}")
            return dependencies_created
    
    def _create_factor_from_config(self, name: str, group: str, subgroup: str, 
                                  data_type: str, tickers: List[str], overwrite: bool = False):
        """
        Create factor domain entity from config using market_data_history_service.
        
        Args:
            name: Factor name
            group: Factor group
            subgroup: Factor subgroup
            data_type: Data type
            tickers: List of tickers to associate with
            overwrite: Whether to overwrite existing factors
        
        Returns:
            Factor entity if created successfully
        """
        try:
            # Use data_loader's factor service to create factor
            if hasattr(self.data_loader, 'factor_data_service'):
                factor_entity = self.data_loader.factor_data_service.create_or_get_factor(
                    name=name,
                    group=group,
                    subgroup=subgroup,
                    data_type=data_type,
                    source='config',
                    definition=f'Factor {name} from {group}/{subgroup} configuration'
                )
                return factor_entity
            else:
                # Fallback to direct creation via market_data_history_service
                factor_entity = Factor(
                    name=name,
                    group=group,
                    subgroup=subgroup,
                    data_type=data_type,
                    source='config',
                    definition=f'Factor {name} from {group}/{subgroup} configuration'
                )
                return factor_entity
                
        except Exception as e:
            print(f"Error creating factor {name}: {str(e)}")
            return None
    
    

    
    
    def _load_ticker_price_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """Load price data for a single ticker from database using repository pattern."""
        try:
            # Get company entity
            company = self.factor_manager.company_share_repository.get_by_ticker(ticker)
            if not company:
                print(f"  ⚠️  Company not found for ticker: {ticker}")
                return None
            company = company[0] if isinstance(company, list) else company
            
            # Define price factor names to fetch
            price_factor_names = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
            price_data = {}
            
            # Fetch each price factor from database
            for factor_name in price_factor_names:
                factor_entity = self.factor_manager.share_factor_repository.get_by_name(factor_name)
                if factor_entity:
                    df = self.factor_manager.share_factor_repository.get_factor_values_df(
                        factor_id=int(factor_entity.id), 
                        entity_id=company.id
                    )
                    if df is not None and hasattr(df, 'empty') and not df.empty:
                        df["date"] = pd.to_datetime(df["date"])
                        df.set_index("date", inplace=True)
                        df["value"] = df["value"].astype(float)
                        # Map to expected column names
                        column_mapping = {
                            'Open': 'open_price',
                            'High': 'high_price', 
                            'Low': 'low_price',
                            'Close': 'close_price',
                            'Adj Close': 'adj_close_price',
                            'Volume': 'volume'
                        }
                        price_data[column_mapping.get(factor_name, factor_name.lower())] = df['value']
            
            if not price_data:
                print(f"  ⚠️  No price data found in database for {ticker}")
                return None
            
            # Combine into single DataFrame
            price_df = pd.DataFrame(price_data)
            price_df.index.name = 'Date'
            return price_df
                
        except Exception as e:
            print(f"  ⚠️  Error loading price data for {ticker}: {str(e)}")
            return None
    
    def _prepare_factor_data(self,date) -> Dict[str, pd.DataFrame]:
        """Prepare factor-enhanced data for all tickers using database-driven approach."""
        
        # Step 1: Ensure all factors exist in database (like backtestRunner)
        results = self._ensure_factors_exist()
        
        # Step 2: Load factor data from database for each ticker
        if not date:
            from datetime import datetime
            date = datetime.now()
        self.data_loader.market_data_history_service.set_frontier(date)
        factor_groups = results['config_factor_details']
        entities = []
        universe = self.config.get('universe', {})
        for entity_class, tickers_list in universe.items():
                for ticker in tickers_list:
                    entity = self.data_loader.market_data_history_service.market_data_service._get_entity_by_ticker(ticker,entity_class)
                    entities.append(entity)
        factor_data = self.data_loader.market_data_history_service._create_or_get_factor_value_batch(factor_groups,entities,date)
        
        print(f"✅ Factor data preparation complete: {len(factor_data)} tickers processed")
        return factor_data
    
    def _normalize_and_enhance_factors(self, factor_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Apply comprehensive factor normalization and enhancement.
        
        This method is inserted between _prepare_factor_data and _create_training_tensors
        to handle missing factors and apply normalization.
        
        Args:
            factor_data: Dictionary of {ticker: DataFrame} with raw factor values
            
        Returns:
            Dictionary of {ticker: DataFrame} with normalized and enhanced factor data
        """
        print("🔧 Applying comprehensive factor normalization and enhancement...")
        
        # Apply the comprehensive normalization pipeline
        enhanced_factor_data = self.factor_normalizer.apply_comprehensive_normalization(factor_data)
        
        # Log the enhancement results
        for ticker, df in enhanced_factor_data.items():
            original_cols = len(factor_data[ticker].columns) if ticker in factor_data else 0
            new_cols = len(df.columns)
            print(f"  ✅ {ticker}: {original_cols} → {new_cols} factors")
        
        print("✅ Factor normalization and enhancement complete")
        return enhanced_factor_data
    
    def _create_training_tensors(self, factor_data: Dict[str, pd.DataFrame], model_type: str) -> Dict[str, Any]:
        """Create training tensors for specified model types."""
        tensor_data = {}
        
        # Configuration from config
        expected_features = (
            self.features_config['momentum_features'] +
            self.features_config['technical_features']
        )
        
        # Create factor name mapping to handle differences between expected and actual column names
        feature_cols = self._map_factor_names(factor_data, expected_features)
        
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
    
    def _map_factor_names(self, factor_data: Dict[str, pd.DataFrame], expected_features: List[str]) -> List[str]:
        """
        Map expected factor names to actual column names in the factor data.
        
        Handles cases where MACD factors or other technical indicators might be
        created with different names than expected in the config.
        """
        if not factor_data:
            return expected_features
        
        # Get all available columns from the first ticker's data
        sample_ticker = list(factor_data.keys())[0]
        available_columns = set(factor_data[sample_ticker].columns)
        
        mapped_features = []
        
        for expected_name in expected_features:
            if expected_name in available_columns:
                # Direct match - use as is
                mapped_features.append(expected_name)
            else:
                # Try to find alternative names for MACD factors
                if expected_name.startswith('macd_'):
                    # Handle MACD factor name mapping
                    # Expected: macd_8_24, macd_16_48, macd_32_96
                    # Possible actual names: macd, MACD, macd_line, etc.
                    
                    # Extract periods from expected name (e.g., "8" and "24" from "macd_8_24")
                    parts = expected_name.split('_')
                    if len(parts) >= 3:
                        fast_period, slow_period = parts[1], parts[2]
                        
                        # Try various possible MACD column names
                        possible_names = [
                            'macd',  # Simple name
                            'MACD',  # Uppercase
                            f'macd_{fast_period}_{slow_period}',  # Expected format
                            f'MACD_{fast_period}_{slow_period}',  # Uppercase variant
                            'macd_line',  # Descriptive name
                            f'macd_line_{fast_period}_{slow_period}',  # Descriptive with periods
                        ]
                        
                        # Find first match
                        matched_name = None
                        for possible_name in possible_names:
                            if possible_name in available_columns:
                                matched_name = possible_name
                                break
                        
                        if matched_name:
                            mapped_features.append(matched_name)
                            print(f"  🔄 Mapped {expected_name} → {matched_name}")
                        else:
                            print(f"  ⚠️  Could not find mapping for {expected_name}")
                            # Still add expected name to let tensor creation handle the missing column
                            mapped_features.append(expected_name)
                    else:
                        print(f"  ⚠️  Invalid MACD factor name format: {expected_name}")
                        mapped_features.append(expected_name)
                else:
                    # For non-MACD factors, try some common alternatives
                    alternative_names = []
                    
                    # For normalized returns
                    if expected_name.startswith('norm_') and expected_name.endswith('_return'):
                        # Try mapping from deep_momentum factors
                        momentum_mapping = {
                            'norm_daily_return': ['deep_momentum_1d', 'momentum_1d'],
                            'norm_monthly_return': ['deep_momentum_5d', 'momentum_5d'], 
                            'norm_quarterly_return': ['deep_momentum_21d', 'momentum_21d'],
                            'norm_biannual_return': ['deep_momentum_63d', 'momentum_63d'],
                            'norm_annual_return': ['deep_momentum_126d', 'momentum_126d']
                        }
                        alternative_names = momentum_mapping.get(expected_name, [])
                    
                    # Find first match
                    matched_name = None
                    for alt_name in alternative_names:
                        if alt_name in available_columns:
                            matched_name = alt_name
                            break
                    
                    if matched_name:
                        mapped_features.append(matched_name)
                        print(f"  🔄 Mapped {expected_name} → {matched_name}")
                    else:
                        print(f"  ⚠️  Could not find mapping for {expected_name}")
                        # Still add expected name to let tensor creation handle the missing column
                        mapped_features.append(expected_name)
        
        print(f"  📋 Feature mapping complete: {len(mapped_features)}/{len(expected_features)} features mapped")
        return mapped_features
    
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
        
        # Get expected feature columns that should NOT be renamed
        expected_features = (
            self.features_config['momentum_features'] +
            self.features_config['technical_features'] +
            self.features_config['volatility_features']
        )
        # Also preserve common required columns
        preserve_columns = expected_features + ['target_returns', 'target_returns_nonscaled', 'daily_vol', 'monthly_vol', 'asset']
        
        for ticker, data in factor_data.items():
            # Add ticker column for asset identification
            data_with_ticker = data.copy()
            data_with_ticker['asset'] = ticker
            
            # Only rename columns that are NOT expected features or required columns
            column_mapping = {}
            for col in data.columns:
                if col not in preserve_columns and col not in ['Date']:
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
    
    def get_trained_model(self) -> PricingModel:
        """Get the trained hybrid model."""
        return self.model