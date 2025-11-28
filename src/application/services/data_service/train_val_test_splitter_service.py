import abc
from copy import deepcopy
import random
from typing import Dict, List, Any, Optional, Tuple

import torch
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler, StandardScaler
import pandas as pd
import numpy as np


def seed_worker(worker_id):
    """Worker initialization function for reproducible data loading."""
    worker_seed = torch.initial_seed() % 2**32
    np.random.seed(worker_seed)
    random.seed(worker_seed)


class TrainValTestSplitterService(abc.ABC):
    """
    Abstract base service for train/validation/test data splitting.
    Provides interface for different splitting strategies.
    """

    @abc.abstractmethod
    def split(self, start, val_delta, test_delta, seed):
        """
        Split data into train, validation, and test sets.
        
        Args:
            start: Starting point for split
            val_delta: Validation period delta
            test_delta: Test period delta
            seed: Random seed for reproducibility
            
        Returns:
            Tuple of train, validation, test data loaders
        """
        pass


class MultivariateTrainValTestSplitterService(TrainValTestSplitterService):
    """
    Service for multivariate time series train/validation/test splitting.
    Implements the data format used in Deep Momentum Networks (https://arxiv.org/pdf/2302.10175.pdf).
    """
    
    def __init__(self, data: Dict, cols: List[str], cat_cols: List[str], 
                 target_col: str, orig_returns_col: str, vol_col: str,
                 timesteps: int = 63, scaling: Optional[str] = None, 
                 batch_size: int = 64, encoder_length: Optional[int] = None):
        """
        Initialize the multivariate splitter service.
        
        Args:
            data: Dictionary of DataFrames with time series data
            cols: List of feature column names
            cat_cols: List of categorical column names
            target_col: Target column name
            orig_returns_col: Original returns column name
            vol_col: Volatility column name
            timesteps: Number of timesteps in sequences
            scaling: Scaling method ('minmax', 'standard', or None)
            batch_size: Batch size for data loaders
            encoder_length: Encoder length for TFT models
        """
        self._data = deepcopy(data)
        self._cols = cols
        self._cat_cols = cat_cols
        self._target_col = target_col
        self._orig_returns_col = orig_returns_col
        self._vol_col = vol_col
        self._scaling = scaling
        self._scalers = {}
        self._timesteps = timesteps
        self._batch_size = batch_size
        self._encoder_length = encoder_length
        
        # Validate inputs to avoid data leakage
        assert self._target_col not in self._cols, "Target column cannot be in feature columns"
        assert self._orig_returns_col not in self._cols, "Original returns column cannot be in feature columns"
        
        if encoder_length is not None:
            assert encoder_length < timesteps, "Encoder length must be less than total timesteps"

    def split(self, start, val_delta, test_delta, seed) -> Tuple[DataLoader, DataLoader, DataLoader, pd.DatetimeIndex, Dict]:
        """
        Split data into train, validation, and test sets with proper temporal ordering.
        
        Args:
            start: Starting date for split
            val_delta: Validation period timedelta
            test_delta: Test period timedelta
            seed: Random seed for reproducibility
            
        Returns:
            Tuple of (train_loader, val_loader, test_loader, test_datetimes, cat_info)
        """
        # Offset to avoid overlap of train/val/test in pandas .loc
        offset_delta = pd.Timedelta('1day')
        
        # Initialize containers for each split
        X_train, X_val, X_test = [], [], []
        y_train, y_val, y_test = [], [], []
        y_train_orig, y_val_orig, y_test_orig = [], [], []
        vol_train, vol_val, vol_test = [], [], []
        test_datetimes = []
        
        for key in self._data.keys():
            # Add index column for splitting
            self._data[key]['idx'] = np.arange(len(self._data[key]))
            train_val_test = self._data[key].loc[:start+val_delta+test_delta]
            
            # Apply scaling if specified
            if self._scaling is not None:
                scaler = self._create_scaler(train_val_test.loc[:start, self._cols])
                self._scalers[(start, key)] = scaler
                train_val_test.loc[:, self._cols] = scaler.transform(train_val_test.loc[:, self._cols])

            # Prepare sequence data
            sequences_data = self._create_sequences(train_val_test)
            X, y, y_orig, vol = sequences_data
            
            # Create train/val/test indices
            train_idx = train_val_test.loc[:start, 'idx']
            val_idx = train_val_test.loc[start+offset_delta:start+val_delta, 'idx']
            test_idx = train_val_test.loc[start+val_delta+offset_delta:start+val_delta+test_delta, 'idx']
            
            # Store test datetimes for alignment checking
            test_dt = train_val_test.loc[train_val_test['idx'].isin(test_idx)].index
            test_datetimes.append(test_dt)
            
            # Split data by indices
            splits = self._split_by_indices(X, y, y_orig, vol, train_idx, val_idx, test_idx)
            X_train_, X_val_, X_test_, y_train_, y_val_, y_test_, y_train_orig_, y_val_orig_, y_test_orig_, vol_train_, vol_val_, vol_test_ = splits
            
            # Remove NaN samples after applying shifts
            X_train_, y_train_, y_train_orig_, vol_train_ = self._remove_nan_samples(
                X_train_, y_train_, y_train_orig_, vol_train_
            )
            
            # Append to master lists
            X_train.append(X_train_)
            X_val.append(X_val_)
            X_test.append(X_test_)
            y_train.append(y_train_)
            y_val.append(y_val_)
            y_test.append(y_test_)
            y_train_orig.append(y_train_orig_)
            y_val_orig.append(y_val_orig_)
            y_test_orig.append(y_test_orig_)
            vol_train.append(vol_train_)
            vol_val.append(vol_val_)
            vol_test.append(vol_test_)
            
            # Clean up auxiliary data
            self._data[key] = self._data[key].drop(['idx'], axis=1)
        
        # Convert to tensors
        arrays = [X_train, X_val, X_test, y_train, y_val, y_test, 
                 y_train_orig, y_val_orig, y_test_orig, vol_train, vol_val, vol_test]
        arrays = [self._to_tensor(arr) for arr in arrays]
        
        X_train, X_val, X_test, y_train, y_val, y_test, y_train_orig, y_val_orig, y_test_orig, vol_train, vol_val, vol_test = arrays
        
        # Handle categorical data if present
        cat_info = {}
        if self._cat_cols:
            X_train, X_val, X_test, cat_info = self._process_categorical_data(
                train_val_test, train_idx, val_idx, test_idx, X_train, X_val, X_test
            )
        
        # Verify temporal alignment
        self._verify_alignment(test_datetimes, X_test)
        
        # Create data loaders
        return self._create_data_loaders(
            X_train, X_val, X_test, y_train, y_val, y_test,
            y_train_orig, y_val_orig, y_test_orig,
            vol_train, vol_val, vol_test, seed, cat_info, test_datetimes[0]
        )

    def _create_scaler(self, data: pd.DataFrame):
        """Create and fit scaler based on scaling method."""
        if self._scaling == 'minmax':
            return MinMaxScaler().fit(data)
        elif self._scaling == 'standard':
            return StandardScaler().fit(data)
        else:
            raise NotImplementedError(f"Scaling method {self._scaling} not implemented")

    def _create_sequences(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Create sequences from time series data."""
        target_timesteps = self._timesteps
        if self._encoder_length is not None:
            target_timesteps -= self._encoder_length
        
        X = np.zeros((len(data), self._timesteps, len(self._cols)))
        y = np.zeros((len(data), target_timesteps, 1))
        y_orig = np.zeros((len(data), target_timesteps, 1))
        vol = np.zeros((len(data), target_timesteps, 1))
        
        # Create feature sequences
        for i, col in enumerate(self._cols):
            for j in range(self._timesteps):
                X[:, j, i] = data[col].shift(self._timesteps - j - 1)
        
        # Create target sequences
        for j in range(target_timesteps):
            y[:, j, 0] = data[self._target_col].shift(target_timesteps - j - 1)
            y_orig[:, j, 0] = data[self._orig_returns_col].shift(target_timesteps - j - 1)
            vol[:, j, 0] = data[self._vol_col].shift(target_timesteps - j - 1)
        
        return X, y, y_orig, vol

    def _split_by_indices(self, X, y, y_orig, vol, train_idx, val_idx, test_idx):
        """Split arrays by provided indices."""
        return (
            X[train_idx], X[val_idx], X[test_idx],
            y[train_idx], y[val_idx], y[test_idx],
            y_orig[train_idx], y_orig[val_idx], y_orig[test_idx],
            vol[train_idx], vol[val_idx], vol[test_idx]
        )

    def _remove_nan_samples(self, X_train, y_train, y_train_orig, vol_train):
        """Remove samples with NaN values created by shifting."""
        return (
            X_train[self._timesteps:],
            y_train[self._timesteps:],
            y_train_orig[self._timesteps:],
            vol_train[self._timesteps:]
        )

    def _to_tensor(self, x_list: List[np.ndarray]) -> torch.Tensor:
        """Convert list of arrays to PyTorch tensor."""
        x = np.concatenate(x_list, axis=2)
        return torch.Tensor(x)

    def _process_categorical_data(self, data, train_idx, val_idx, test_idx, X_train, X_val, X_test):
        """Process categorical features if present."""
        X_cat = np.zeros((len(data), self._timesteps, len(self._cat_cols)))
        
        for i, col in enumerate(self._cat_cols):
            for j in range(self._timesteps):
                X_cat[:, j, i] = data[col].shift(self._timesteps - j - 1)
        
        X_train_cat = torch.Tensor(X_cat[train_idx])[self._timesteps:]
        X_val_cat = torch.Tensor(X_cat[val_idx])
        X_test_cat = torch.Tensor(X_cat[test_idx])
        
        if self._encoder_length is None:
            # For non-TFT models, concatenate categorical with continuous
            X_train = torch.cat([X_train, X_train_cat], dim=2)
            X_val = torch.cat([X_val, X_val_cat], dim=2)
            X_test = torch.cat([X_test, X_test_cat], dim=2)
            cat_info = {}
        else:
            # For TFT models, keep separate and collect categorical info
            cat_info = {i: len(torch.unique(X_train_cat[..., i])) 
                       for i in range(len(self._cat_cols))}
        
        return X_train, X_val, X_test, cat_info

    def _verify_alignment(self, test_datetimes: List[pd.DatetimeIndex], X_test: torch.Tensor):
        """Verify temporal alignment across different keys."""
        for i in range(1, len(test_datetimes)):
            assert np.all((test_datetimes[i] - test_datetimes[0]) == pd.Timedelta(0)), \
                "Test datetimes not aligned across keys"
        assert len(X_test) == len(test_datetimes[0]), \
            "Test data length mismatch with datetime index"

    def _create_data_loaders(self, X_train, X_val, X_test, y_train, y_val, y_test,
                           y_train_orig, y_val_orig, y_test_orig, vol_train, vol_val, vol_test,
                           seed, cat_info, test_datetimes):
        """Create PyTorch data loaders with proper configuration."""
        # Set up reproducible batch sampling
        g = torch.Generator()
        g.manual_seed(seed)
        
        if self._encoder_length is None:
            # Standard data loaders for non-TFT models
            train_loader = DataLoader(
                TensorDataset(X_train, y_train, y_train_orig, vol_train),
                shuffle=True, batch_size=self._batch_size,
                worker_init_fn=seed_worker, generator=g
            )
            val_loader = DataLoader(
                TensorDataset(X_val, y_val, y_val_orig, vol_val),
                shuffle=False, batch_size=self._batch_size
            )
            test_loader = DataLoader(
                TensorDataset(X_test, y_test, y_test_orig, vol_test),
                shuffle=False, batch_size=self._batch_size
            )
        else:
            # TFT-specific data loaders with encoder/decoder split
            train_loader, val_loader, test_loader = self._create_tft_data_loaders(
                X_train, X_val, X_test, y_train, y_val, y_test,
                y_train_orig, y_val_orig, y_test_orig, vol_train, vol_val, vol_test, g
            )
        
        return train_loader, val_loader, test_loader, test_datetimes, cat_info

    def _create_tft_data_loaders(self, X_train, X_val, X_test, y_train, y_val, y_test,
                               y_train_orig, y_val_orig, y_test_orig, vol_train, vol_val, vol_test, generator):
        """Create TFT-specific data loaders with encoder/decoder splitting."""
        def _split_encoder_decoder(x, t):
            """Split tensor into encoder and decoder parts."""
            x_enc = x[:, :t, :]
            x_dec = x[:, t:, :]
            
            x_enc_length = torch.ones(len(x)).long().fill_(x_enc.shape[1])
            x_dec_length = torch.ones(len(x)).long().fill_(x_dec.shape[1])
            
            return x_enc, x_dec, x_enc_length, x_dec_length
        
        # Split into encoder/decoder parts
        splits_train = _split_encoder_decoder(X_train, self._encoder_length)
        splits_val = _split_encoder_decoder(X_val, self._encoder_length)
        splits_test = _split_encoder_decoder(X_test, self._encoder_length)
        
        X_train_enc_real, X_train_dec_real, X_train_enc_len, X_train_dec_len = splits_train
        X_val_enc_real, X_val_dec_real, X_val_enc_len, X_val_dec_len = splits_val
        X_test_enc_real, X_test_dec_real, X_test_enc_len, X_test_dec_len = splits_test
        
        # Handle categorical data for TFT
        if not self._cat_cols:
            # Create dummy categorical tensors
            X_train_cat = torch.zeros_like(X_train).long()
            X_val_cat = torch.zeros_like(X_val).long()
            X_test_cat = torch.zeros_like(X_test).long()
        else:
            # Use actual categorical data (processed earlier)
            X_train_cat = X_train_cat.long()
            X_val_cat = X_val_cat.long()
            X_test_cat = X_test_cat.long()
        
        # Split categorical data
        X_train_enc_cat, X_train_dec_cat, _, _ = _split_encoder_decoder(X_train_cat, self._encoder_length)
        X_val_enc_cat, X_val_dec_cat, _, _ = _split_encoder_decoder(X_val_cat, self._encoder_length)
        X_test_enc_cat, X_test_dec_cat, _, _ = _split_encoder_decoder(X_test_cat, self._encoder_length)
        
        # Create TFT data loaders
        train_loader = DataLoader(
            TensorDataset(X_train_enc_real, X_train_enc_cat, X_train_dec_real, X_train_dec_cat,
                         X_train_enc_len, X_train_dec_len, y_train, y_train_orig, vol_train),
            shuffle=True, batch_size=self._batch_size,
            worker_init_fn=seed_worker, generator=generator
        )
        
        val_loader = DataLoader(
            TensorDataset(X_val_enc_real, X_val_enc_cat, X_val_dec_real, X_val_dec_cat,
                         X_val_enc_len, X_val_dec_len, y_val, y_val_orig, vol_val),
            shuffle=False, batch_size=self._batch_size
        )
        
        test_loader = DataLoader(
            TensorDataset(X_test_enc_real, X_test_enc_cat, X_test_dec_real, X_test_dec_cat,
                         X_test_enc_len, X_test_dec_len, y_test, y_test_orig, vol_test),
            shuffle=False, batch_size=self._batch_size
        )
        
        return train_loader, val_loader, test_loader

    def get_scalers(self) -> Dict:
        """Get fitted scalers for inverse transformations."""
        return self._scalers


class UnivariateTrainValTestSplitterService(TrainValTestSplitterService):
    """
    Service for univariate time series train/validation/test splitting.
    Simpler implementation for single-variable time series.
    """
    
    def __init__(self, data: pd.Series, timesteps: int = 63, 
                 scaling: Optional[str] = None, batch_size: int = 64):
        """
        Initialize the univariate splitter service.
        
        Args:
            data: Pandas Series with time series data
            timesteps: Number of timesteps in sequences
            scaling: Scaling method ('minmax', 'standard', or None)
            batch_size: Batch size for data loaders
        """
        self.data = data
        self.timesteps = timesteps
        self.scaling = scaling
        self.batch_size = batch_size
        self.scaler = None

    def split(self, start=None, val_delta=None, test_delta=None, seed=42, 
             train_ratio: float = 0.7, val_ratio: float = 0.15, 
             test_ratio: float = 0.15) -> Tuple[DataLoader, DataLoader, DataLoader]:
        """
        Split univariate data into train, validation, and test sets.
        
        Args:
            start: Starting date for split (if None, use ratio-based splitting)
            val_delta: Validation period timedelta (if None, use ratio-based splitting)
            test_delta: Test period timedelta (if None, use ratio-based splitting)
            seed: Random seed for reproducibility
            train_ratio: Proportion for training set (used when start=None)
            val_ratio: Proportion for validation set (used when start=None)
            test_ratio: Proportion for test set (used when start=None)
            
        Returns:
            Tuple of (train_loader, val_loader, test_loader) or 
            (train_loader, val_loader, test_loader, test_dt, cat_info) for datetime-based splits
        """
        # Check if datetime-based splitting is requested
        if start is not None and val_delta is not None and test_delta is not None:
            # Return compatible format for MLP service (matching multivariate interface)
            train_loader, val_loader, test_loader = self._create_ratio_based_split(train_ratio, val_ratio, test_ratio, seed)
            # For compatibility, return test date and empty cat_info
            import pandas as pd
            test_dt = pd.Timestamp.now()  # Dummy timestamp for compatibility
            cat_info = {}
            return train_loader, val_loader, test_loader, test_dt, cat_info
        
        # Standard ratio-based splitting - return compatible format with placeholders
        if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-6:
            raise ValueError("Ratios must sum to 1.0")
        
        train_loader, val_loader, test_loader = self._create_ratio_based_split(train_ratio, val_ratio, test_ratio, seed)
        # For compatibility with MLP service, return placeholders for test_dt and cat_info
        import pandas as pd
        test_dt = pd.Timestamp.now()  # Dummy timestamp for compatibility
        cat_info = {}
        return train_loader, val_loader, test_loader, test_dt, cat_info
    
    def _create_ratio_based_split(self, train_ratio: float, val_ratio: float, test_ratio: float, seed: int):
        """Create data splits based on ratios."""
        # Apply scaling if specified
        data_scaled = self.data.values.reshape(-1, 1)
        if self.scaling == 'minmax':
            self.scaler = MinMaxScaler()
            data_scaled = self.scaler.fit_transform(data_scaled).flatten()
        elif self.scaling == 'standard':
            self.scaler = StandardScaler()
            data_scaled = self.scaler.fit_transform(data_scaled).flatten()
        else:
            data_scaled = data_scaled.flatten()
        
        # Create sequences
        X, y = self._create_univariate_sequences(data_scaled)
        
        # Split data
        n = len(X)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        
        X_train, X_val, X_test = X[:train_end], X[train_end:val_end], X[val_end:]
        y_train, y_val, y_test = y[:train_end], y[train_end:val_end], y[val_end:]
        
        # Convert to tensors
        X_train = torch.FloatTensor(X_train).unsqueeze(-1)  # Add feature dimension
        X_val = torch.FloatTensor(X_val).unsqueeze(-1)
        X_test = torch.FloatTensor(X_test).unsqueeze(-1)
        y_train = torch.FloatTensor(y_train).unsqueeze(-1)
        y_val = torch.FloatTensor(y_val).unsqueeze(-1)
        y_test = torch.FloatTensor(y_test).unsqueeze(-1)
        
        # Create data loaders
        g = torch.Generator()
        g.manual_seed(seed)
        
        train_loader = DataLoader(
            TensorDataset(X_train, y_train),
            shuffle=True, batch_size=self.batch_size,
            worker_init_fn=seed_worker, generator=g
        )
        val_loader = DataLoader(
            TensorDataset(X_val, y_val),
            shuffle=False, batch_size=self.batch_size
        )
        test_loader = DataLoader(
            TensorDataset(X_test, y_test),
            shuffle=False, batch_size=self.batch_size
        )
        
        return train_loader, val_loader, test_loader

    def _create_univariate_sequences(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for univariate time series."""
        X, y = [], []
        
        for i in range(len(data) - self.timesteps):
            X.append(data[i:i + self.timesteps])
            y.append(data[i + self.timesteps])
        
        return np.array(X), np.array(y)