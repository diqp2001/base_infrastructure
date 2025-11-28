"""
Tensor splitting utilities for spatiotemporal model training.

Provides unified interface for creating multivariate and univariate
tensor splitters with factor-enhanced data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any

from application.services.data_service.train_val_test_splitter_service import MultivariateTrainValTestSplitterService, UnivariateTrainValTestSplitterService

from ..config import DEFAULT_CONFIG


class TensorSplitterManager:
    """
    Manager for creating and configuring tensor splitters for spatiotemporal models.
    
    Handles both multivariate (TFT) and univariate (MLP) tensor creation
    with appropriate configuration for factor-enhanced data.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize tensor splitter manager.
        
        Args:
            config: Configuration dictionary (uses default if None)
        """
        self.config = config or DEFAULT_CONFIG['SPATIOTEMPORAL']
        self.training_config = self.config['TRAINING_CONFIG']
        self.features_config = self.config['FEATURES']
    
    def create_multivariate_tensors(self,
                                  data: pd.DataFrame,
                                  cols: List[str],
                                  target_col: str = 'target_returns',
                                  timesteps: int = 63,
                                  batch_size: int = 64,
                                  encoder_length: Optional[int] = None,
                                  scaling: Optional[str] = None) -> MultivariateTrainValTestSplitterService:
        """
        Create multivariate tensor splitter for TFT models.
        
        Args:
            data: Input DataFrame with factor features
            cols: List of feature columns to use
            target_col: Target column name
            timesteps: Number of timesteps in sequences
            batch_size: Batch size for training
            encoder_length: Encoder sequence length for TFT
            scaling: Scaling method ('standard', 'minmax', or None)
            
        Returns:
            Configured MultivariateTrainValTestSplitterService
        """
        print(f"🔄 Creating multivariate tensors: {len(cols)} features, {timesteps} timesteps")
        
        # Set default values from config if not provided
        if encoder_length is None:
            encoder_length = self.training_config['encoder_length']
        
        if scaling is None:
            scaling = self.training_config.get('scaling')
        
        # Prepare required columns
        cat_cols = self._identify_categorical_columns(data, cols)
        orig_returns_col = f'{target_col}_nonscaled'
        vol_col = 'daily_vol'
        
        # Ensure required columns exist
        data = self._ensure_required_columns(data, target_col, orig_returns_col, vol_col)
        
        # Validate feature columns
        available_cols = [col for col in cols if col in data.columns]
        if len(available_cols) < len(cols):
            missing_cols = set(cols) - set(available_cols)
            print(f"  ⚠️  Missing columns: {missing_cols}")
            print(f"  ✅ Using {len(available_cols)} available features")
        
        try:
            splitter = MultivariateTrainValTestSplitterService(
                data=data,
                cols=available_cols,
                cat_cols=cat_cols,
                target_col=target_col,
                orig_returns_col=orig_returns_col,
                vol_col=vol_col,
                timesteps=timesteps,
                scaling=scaling,
                batch_size=batch_size,
                encoder_length=encoder_length
            )
            
            print(f"  ✅ Multivariate splitter created successfully")
            return splitter
            
        except Exception as e:
            print(f"  ❌ Error creating multivariate splitter: {str(e)}")
            # Create fallback with minimal requirements
            return self._create_fallback_multivariate_splitter(
                data, available_cols, target_col, timesteps, batch_size
            )
    
    def create_univariate_tensors(self,
                                data: Dict[str, pd.DataFrame],
                                cols: List[str],
                                target_col: str = 'target_returns',
                                timesteps: int = 21,
                                encoder_length: Optional[int] = None,
                                scaling: Optional[str] = None) -> UnivariateTrainValTestSplitterService:
        """
        Create univariate tensor splitter for MLP models.
        
        Args:
            data: Dictionary of DataFrames by asset/ticker
            cols: List of feature columns to use
            target_col: Target column name
            timesteps: Number of timesteps in sequences
            encoder_length: Encoder length (None for MLP)
            scaling: Scaling method
            
        Returns:
            Configured UnivariateTrainValTestSplitterService
        """
        print(f"🔄 Creating univariate tensors: {len(data)} assets, {len(cols)} features")
        
        # Set defaults from config
        if scaling is None:
            scaling = self.training_config.get('scaling')
        
        # Prepare data with asset information
        prepared_data = {}
        for asset, df in data.items():
            asset_data = df.copy()
            asset_data['asset'] = asset
            
            # Ensure required columns exist
            orig_returns_col = f'{target_col}_nonscaled'
            vol_col = 'daily_vol'
            asset_data = self._ensure_required_columns(asset_data, target_col, orig_returns_col, vol_col)
            
            prepared_data[asset] = asset_data
        
        # Identify categorical columns
        sample_data = list(prepared_data.values())[0]
        cat_cols = self._identify_categorical_columns(sample_data, cols + ['asset'])
        
        # Validate feature columns
        available_cols = [col for col in cols if col in sample_data.columns]
        if len(available_cols) < len(cols):
            missing_cols = set(cols) - set(available_cols)
            print(f"  ⚠️  Missing columns: {missing_cols}")
            print(f"  ✅ Using {len(available_cols)} available features")
        
        try:
            # Convert prepared_data dict to a single Series for univariate splitter
            # Combine all asset data into one series for univariate analysis
            combined_data = []
            for asset, df in prepared_data.items():
                # Use the target column as the primary data series
                if target_col in df.columns:
                    combined_data.extend(df[target_col].dropna().tolist())
            
            if not combined_data:
                raise ValueError(f"No valid data found for target column '{target_col}'")
            
            # Convert to pandas Series
            import pandas as pd
            data_series = pd.Series(combined_data)
            
            splitter = UnivariateTrainValTestSplitterService(
                data=data_series,
                timesteps=timesteps,
                scaling=scaling,
                batch_size=64  # Default batch size
            )
            
            print(f"  ✅ Univariate splitter created successfully")
            return splitter
            
        except Exception as e:
            print(f"  ❌ Error creating univariate splitter: {str(e)}")
            # Create fallback
            return self._create_fallback_univariate_splitter(
                prepared_data, available_cols, target_col, timesteps
            )
    
    def _identify_categorical_columns(self, data: pd.DataFrame, cols: List[str]) -> List[str]:
        """Identify categorical columns from the feature list."""
        categorical_cols = []
        
        for col in cols:
            if col in data.columns:
                # Check if column contains non-numeric data or has limited unique values
                if (data[col].dtype == 'object' or 
                    data[col].dtype.name == 'category' or
                    col in ['asset', 'ticker', 'sector']):
                    categorical_cols.append(col)
        
        return categorical_cols
    
    def _ensure_required_columns(self, data: pd.DataFrame, 
                               target_col: str, 
                               orig_returns_col: str, 
                               vol_col: str) -> pd.DataFrame:
        """Ensure required columns exist in the data."""
        result_data = data.copy()
        
        # Ensure target column exists
        if target_col not in result_data.columns:
            if 'close_price' in result_data.columns:
                result_data[target_col] = result_data['close_price'].pct_change().shift(-1)
            else:
                result_data[target_col] = 0.0
        
        # Ensure non-scaled target exists
        if orig_returns_col not in result_data.columns:
            result_data[orig_returns_col] = result_data[target_col].copy()
        
        # Ensure volatility column exists
        if vol_col not in result_data.columns:
            if target_col in result_data.columns:
                result_data[vol_col] = result_data[target_col].rolling(window=21).std()
            else:
                result_data[vol_col] = 0.01  # Default volatility
        
        # Fill missing values
        result_data = result_data.ffill().bfill().fillna(0)
        
        return result_data
    
    def _create_fallback_multivariate_splitter(self,
                                             data: pd.DataFrame,
                                             cols: List[str],
                                             target_col: str,
                                             timesteps: int,
                                             batch_size: int) -> MultivariateTrainValTestSplitterService:
        """Create a fallback multivariate splitter with minimal configuration."""
        print("  🔧 Creating fallback multivariate splitter...")
        
        # Use basic configuration
        fallback_data = data.copy()
        fallback_cols = [col for col in cols[:5] if col in data.columns]  # Use first 5 available
        
        if not fallback_cols:
            # Create minimal features
            if 'close_price' in data.columns:
                fallback_data['returns'] = fallback_data['close_price'].pct_change()
                fallback_cols = ['returns']
            else:
                fallback_data['dummy_feature'] = np.random.randn(len(fallback_data))
                fallback_cols = ['dummy_feature']
        
        return MultivariateTrainValTestSplitterService(
            data=fallback_data,
            cols=fallback_cols,
            cat_cols=[],
            target_col=target_col,
            orig_returns_col=f'{target_col}_nonscaled',
            vol_col='daily_vol',
            timesteps=timesteps,
            scaling=None,
            batch_size=batch_size,
            encoder_length=21
        )
    
    def _create_fallback_univariate_splitter(self,
                                           data: Dict[str, pd.DataFrame],
                                           cols: List[str],
                                           target_col: str,
                                           timesteps: int) -> UnivariateTrainValTestSplitterService:
        """Create a fallback univariate splitter with minimal configuration."""
        print("  🔧 Creating fallback univariate splitter...")
        
        fallback_data = {}
        fallback_cols = [col for col in cols[:5] if col in list(data.values())[0].columns]
        
        if not fallback_cols:
            fallback_cols = ['returns']
        
        for asset, df in data.items():
            asset_data = df.copy()
            asset_data['asset'] = asset
            
            # Ensure basic features exist
            if 'returns' not in asset_data.columns and 'close_price' in asset_data.columns:
                asset_data['returns'] = asset_data['close_price'].pct_change()
            
            fallback_data[asset] = asset_data
        
        # Convert fallback_data to a single Series like in the main method
        combined_fallback_data = []
        for asset, df in fallback_data.items():
            if target_col in df.columns:
                combined_fallback_data.extend(df[target_col].dropna().tolist())
        
        if not combined_fallback_data:
            # Create dummy data if no valid data found
            combined_fallback_data = [0.0] * 100  # Create 100 dummy data points
        
        import pandas as pd
        fallback_series = pd.Series(combined_fallback_data)
        
        return UnivariateTrainValTestSplitterService(
            data=fallback_series,
            timesteps=timesteps,
            scaling=None,
            batch_size=64
        )
    
    def validate_data_for_tensors(self, data: pd.DataFrame, required_cols: List[str]) -> Dict[str, Any]:
        """
        Validate data for tensor creation.
        
        Args:
            data: Input DataFrame
            required_cols: List of required columns
            
        Returns:
            Validation report
        """
        validation_report = {
            'is_valid': True,
            'issues': [],
            'warnings': [],
            'data_shape': data.shape,
            'available_columns': list(data.columns),
            'missing_columns': []
        }
        
        # Check for missing columns
        missing_cols = set(required_cols) - set(data.columns)
        if missing_cols:
            validation_report['missing_columns'] = list(missing_cols)
            validation_report['issues'].append(f"Missing required columns: {missing_cols}")
        
        # Check for sufficient data
        if len(data) < 100:
            validation_report['warnings'].append(f"Limited data: only {len(data)} records")
        
        # Check for missing values
        missing_values = data.isnull().sum()
        if missing_values.sum() > 0:
            validation_report['warnings'].append(f"Missing values found: {missing_values.sum()} total")
        
        # Check data types
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        non_numeric = set(required_cols) - set(numeric_cols)
        if non_numeric:
            validation_report['warnings'].append(f"Non-numeric columns: {non_numeric}")
        
        # Overall validation
        if validation_report['issues']:
            validation_report['is_valid'] = False
        
        return validation_report
    
    def get_recommended_config(self, data_shape: tuple, model_type: str) -> Dict[str, Any]:
        """
        Get recommended tensor configuration based on data characteristics.
        
        Args:
            data_shape: Shape of input data (rows, columns)
            model_type: 'tft' or 'mlp'
            
        Returns:
            Recommended configuration
        """
        rows, cols = data_shape
        
        base_config = {
            'batch_size': min(64, max(16, rows // 100)),
            'scaling': 'standard' if rows > 1000 else None
        }
        
        if model_type == 'tft':
            base_config.update({
                'timesteps': min(63, max(21, rows // 50)),
                'encoder_length': min(42, max(14, rows // 75))
            })
        else:  # mlp
            base_config.update({
                'timesteps': min(21, max(7, rows // 100)),
                'encoder_length': None
            })
        
        return base_config