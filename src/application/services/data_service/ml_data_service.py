import pandas as pd
from typing import Optional, Any, Dict, List
from ..database_service.database_service import DatabaseService
from .data_service import DataService


class MLDataService(DataService):
    """
    Service for managing machine learning-specific data operations.
    Handles ML data preprocessing, feature engineering, and model data preparation.
    """

    def __init__(self, database_service: DatabaseService, project_name: str, scaler: str = 'standard'):
        """
        Initialize the ML data service.
        
        Args:
            database_service: DatabaseService instance for data operations
            project_name: Specific project context for ML operations
            scaler: Scaling method for data normalization
        """
        super().__init__(database_service, scaler)
        self.project_name = project_name

    def get_training_data(self, query_key: str) -> Optional[pd.DataFrame]:
        """
        Retrieve training data from the database based on a specific query key.
        
        Args:
            query_key: The query key to fetch the relevant data from configuration
            
        Returns:
            Training data as a DataFrame or None if query not found
        """
        try:
            # Get query from database service configuration
            query = self.database_service.get_query(query_key)
            if query:
                return self.database_service.execute_query(query)
            else:
                print(f"No query found for key: {query_key}")
                return None
        except Exception as e:
            print(f"Error retrieving training data for key {query_key}: {e}")
            return None

    def preprocess_ml_data(self, dataframe: pd.DataFrame, handle_nulls: bool = True,
                          feature_columns: Optional[List[str]] = None,
                          target_column: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Perform ML-specific preprocessing on the dataframe.
        
        Args:
            dataframe: The DataFrame to preprocess
            handle_nulls: Whether to handle missing values
            feature_columns: List of feature column names
            target_column: Target column name
            
        Returns:
            Dictionary containing processed features and target DataFrames
        """
        processed_data = dataframe.copy()
        
        # Basic preprocessing
        if handle_nulls:
            processed_data = self.handle_missing_values(processed_data)
        
        # Scale the data
        processed_data = self.scale_data(processed_data)
        
        # Separate features and target if specified
        result = {'data': processed_data}
        
        if feature_columns:
            result['features'] = processed_data[feature_columns]
        
        if target_column and target_column in processed_data.columns:
            result['target'] = processed_data[target_column]
            result['features_only'] = processed_data.drop(columns=[target_column])
        
        return result

    def create_sequences(self, data: pd.DataFrame, sequence_length: int, 
                        target_column: Optional[str] = None) -> tuple:
        """
        Create sequences for time series ML models.
        
        Args:
            data: Input DataFrame
            sequence_length: Length of each sequence
            target_column: Target column name (if any)
            
        Returns:
            Tuple of (sequences, targets) as numpy arrays
        """
        import numpy as np
        
        sequences = []
        targets = []
        
        for i in range(len(data) - sequence_length):
            seq = data.iloc[i:i+sequence_length].values
            sequences.append(seq)
            
            if target_column:
                target = data[target_column].iloc[i+sequence_length]
                targets.append(target)
        
        sequences = np.array(sequences)
        targets = np.array(targets) if targets else None
        
        return sequences, targets

    def feature_engineering_ml(self, data: pd.DataFrame, 
                              include_technical: bool = True,
                              include_statistical: bool = True,
                              lookback_periods: List[int] = None) -> pd.DataFrame:
        """
        Perform ML-specific feature engineering.
        
        Args:
            data: Input DataFrame
            include_technical: Whether to include technical indicators
            include_statistical: Whether to include statistical features
            lookback_periods: List of lookback periods for rolling features
            
        Returns:
            DataFrame with engineered features
        """
        if lookback_periods is None:
            lookback_periods = [5, 10, 20, 50]
        
        engineered_data = data.copy()
        
        # Statistical features
        if include_statistical:
            for col in data.select_dtypes(include=[np.number]).columns:
                for period in lookback_periods:
                    # Rolling statistics
                    engineered_data[f'{col}_mean_{period}'] = data[col].rolling(period).mean()
                    engineered_data[f'{col}_std_{period}'] = data[col].rolling(period).std()
                    engineered_data[f'{col}_min_{period}'] = data[col].rolling(period).min()
                    engineered_data[f'{col}_max_{period}'] = data[col].rolling(period).max()
                    
                    # Returns
                    engineered_data[f'{col}_return_{period}'] = data[col].pct_change(period)
                    
                    # Z-score
                    mean = data[col].rolling(period).mean()
                    std = data[col].rolling(period).std()
                    engineered_data[f'{col}_zscore_{period}'] = (data[col] - mean) / (std + 1e-9)
        
        # Technical indicators (if applicable)
        if include_technical and 'close' in data.columns:
            # Simple moving averages
            for period in lookback_periods:
                engineered_data[f'sma_{period}'] = data['close'].rolling(period).mean()
                
            # Exponential moving averages
            for period in [12, 26]:
                engineered_data[f'ema_{period}'] = data['close'].ewm(span=period).mean()
        
        return engineered_data.dropna()

    def split_data_for_ml(self, data: pd.DataFrame, target_column: str,
                         train_ratio: float = 0.7, val_ratio: float = 0.15,
                         test_ratio: float = 0.15) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Split data into train, validation, and test sets for ML.
        
        Args:
            data: Input DataFrame
            target_column: Name of the target column
            train_ratio: Proportion for training set
            val_ratio: Proportion for validation set
            test_ratio: Proportion for test set
            
        Returns:
            Dictionary containing train/val/test splits with features and targets
        """
        if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-6:
            raise ValueError("Ratios must sum to 1.0")
        
        n = len(data)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        
        # Split indices
        train_data = data.iloc[:train_end]
        val_data = data.iloc[train_end:val_end]
        test_data = data.iloc[val_end:]
        
        # Create feature/target splits
        feature_columns = [col for col in data.columns if col != target_column]
        
        splits = {
            'train': {
                'features': train_data[feature_columns],
                'target': train_data[target_column]
            },
            'val': {
                'features': val_data[feature_columns],
                'target': val_data[target_column]
            },
            'test': {
                'features': test_data[feature_columns],
                'target': test_data[target_column]
            }
        }
        
        return splits

    def handle_outliers(self, data: pd.DataFrame, method: str = 'iqr',
                       threshold: float = 1.5) -> pd.DataFrame:
        """
        Handle outliers in the dataset.
        
        Args:
            data: Input DataFrame
            method: Method for outlier detection ('iqr', 'zscore')
            threshold: Threshold for outlier detection
            
        Returns:
            DataFrame with outliers handled
        """
        data_clean = data.copy()
        
        for col in data.select_dtypes(include=[np.number]).columns:
            if method == 'iqr':
                Q1 = data[col].quantile(0.25)
                Q3 = data[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                
                # Cap outliers
                data_clean[col] = data[col].clip(lower_bound, upper_bound)
                
            elif method == 'zscore':
                mean = data[col].mean()
                std = data[col].std()
                z_scores = np.abs((data[col] - mean) / std)
                
                # Replace outliers with mean
                data_clean.loc[z_scores > threshold, col] = mean
        
        return data_clean

    def create_lag_features(self, data: pd.DataFrame, columns: List[str],
                          lags: List[int]) -> pd.DataFrame:
        """
        Create lagged features for time series analysis.
        
        Args:
            data: Input DataFrame
            columns: List of columns to create lags for
            lags: List of lag periods
            
        Returns:
            DataFrame with lag features
        """
        lagged_data = data.copy()
        
        for col in columns:
            for lag in lags:
                lagged_data[f'{col}_lag_{lag}'] = data[col].shift(lag)
        
        return lagged_data.dropna()

    def create_rolling_features(self, data: pd.DataFrame, columns: List[str],
                              windows: List[int], operations: List[str]) -> pd.DataFrame:
        """
        Create rolling window features.
        
        Args:
            data: Input DataFrame
            columns: List of columns to create rolling features for
            windows: List of window sizes
            operations: List of operations ('mean', 'std', 'min', 'max', 'sum')
            
        Returns:
            DataFrame with rolling features
        """
        rolling_data = data.copy()
        
        for col in columns:
            for window in windows:
                for operation in operations:
                    if operation == 'mean':
                        rolling_data[f'{col}_rolling_{operation}_{window}'] = \
                            data[col].rolling(window).mean()
                    elif operation == 'std':
                        rolling_data[f'{col}_rolling_{operation}_{window}'] = \
                            data[col].rolling(window).std()
                    elif operation == 'min':
                        rolling_data[f'{col}_rolling_{operation}_{window}'] = \
                            data[col].rolling(window).min()
                    elif operation == 'max':
                        rolling_data[f'{col}_rolling_{operation}_{window}'] = \
                            data[col].rolling(window).max()
                    elif operation == 'sum':
                        rolling_data[f'{col}_rolling_{operation}_{window}'] = \
                            data[col].rolling(window).sum()
        
        return rolling_data.dropna()

    def prepare_data_for_model(self, data: pd.DataFrame, target_column: str,
                              sequence_length: Optional[int] = None,
                              include_feature_engineering: bool = True) -> Dict[str, Any]:
        """
        Comprehensive data preparation for ML models.
        
        Args:
            data: Input DataFrame
            target_column: Target column name
            sequence_length: Sequence length for time series models
            include_feature_engineering: Whether to perform feature engineering
            
        Returns:
            Dictionary with prepared data and metadata
        """
        prepared_data = data.copy()
        
        # Feature engineering
        if include_feature_engineering:
            prepared_data = self.feature_engineering_ml(prepared_data)
        
        # Handle outliers
        prepared_data = self.handle_outliers(prepared_data)
        
        # Split data
        splits = self.split_data_for_ml(prepared_data, target_column)
        
        # Create sequences if needed
        if sequence_length:
            train_seq, train_targets = self.create_sequences(
                splits['train']['features'], sequence_length, target_column
            )
            val_seq, val_targets = self.create_sequences(
                splits['val']['features'], sequence_length, target_column
            )
            test_seq, test_targets = self.create_sequences(
                splits['test']['features'], sequence_length, target_column
            )
            
            return {
                'train_sequences': train_seq,
                'train_targets': train_targets,
                'val_sequences': val_seq,
                'val_targets': val_targets,
                'test_sequences': test_seq,
                'test_targets': test_targets,
                'feature_names': list(splits['train']['features'].columns),
                'sequence_length': sequence_length
            }
        
        return {
            'splits': splits,
            'feature_names': list(splits['train']['features'].columns),
            'target_name': target_column
        }