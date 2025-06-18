from copy import deepcopy
import random

from torch.utils.data import DataLoader, TensorDataset, Dataset
from sklearn.preprocessing import MinMaxScaler, StandardScaler
import pandas as pd
import numpy as np
import torch
from .train_val_test_splitter import TrainValTestSplitter


def seed_worker(worker_id):
    worker_seed = torch.initial_seed() % 2**32
    np.random.seed(worker_seed)
    random.seed(worker_seed)

# data format used in https://arxiv.org/pdf/2302.10175.pdf
class MultivariateTrainValTestSplitter(TrainValTestSplitter):
    
    def __init__(self, data, cols, cat_cols, target_col, orig_returns_col, vol_col,
                 timesteps=63, scaling=None, batch_size=64, encoder_length=None):
        self._data = deepcopy(data)
        self._cols = cols
        self._cat_cols = cat_cols
        self._target_col = target_col
        self._orig_returns_col = orig_returns_col
        self._vol_col = vol_col
        self._scaling = scaling
        self._scalers = {}
        self._timesteps = timesteps
        self._batch_size= batch_size
        self._encoder_length = encoder_length
        
        # to avoid data leak
        assert self._target_col not in self._cols
        assert self._orig_returns_col not in self._cols
        if encoder_length is not None:
            assert encoder_length < timesteps
        
        
    def split(self, start, val_delta, test_delta, seed):        
        
        # used to avoid overlap of train/val/test in pandas .loc
        offset_delta = pd.Timedelta('1day')
        
        X_train, X_val, X_test = [], [], []
        y_train, y_val, y_test = [], [], []
        y_train_orig, y_val_orig, y_test_orig = [], [], []
        vol_train, vol_val, vol_test = [], [], []
        
        test_datetimes = []
        
        for key in self._data.keys():
            # used to split data into train/val/test
            self._data[key]['idx'] = np.arange(len(self._data[key]))
            train_val_test = self._data[key].loc[:start+val_delta+test_delta]
            
            
            # optionally scale features
            if self._scaling is not None:
                if self._scaling == 'minmax':
                    scaler = MinMaxScaler().fit(train_val_test.loc[:start, self._cols])
                elif self._scaling == 'standard':
                    scaler = StandardScaler().fit(train_val_test.loc[:start, self._cols])
                
                else:
                    raise NotImplementedError
                
                self._scalers[(start, key)] = scaler

                train_val_test.loc[:, self._cols] = scaler.transform(train_val_test.loc[:, self._cols])

            cols = self._cols
            
            target_timesteps = self._timesteps
            if self._encoder_length is not None:
                # in case of tft model, create target lookback equal to length of decoder output
                target_timesteps -= self._encoder_length
            
            X = np.zeros((len(train_val_test), self._timesteps, len(cols)))
            y = np.zeros((len(train_val_test), target_timesteps, 1))

            #collect non scaled target returns data for further model evaluation
            y_orig = np.zeros((len(train_val_test), target_timesteps, 1))
            #collect volatility data for turnover regularization and/or evaluation
            vol = np.zeros((len(train_val_test), target_timesteps, 1))
            
            for i, col in enumerate(cols):
                for j in range(self._timesteps):
                    X[:, j, i] = train_val_test[col].shift(self._timesteps - j - 1)
                    

            for j in range(target_timesteps):
                y[:, j, 0] = train_val_test[self._target_col].shift(target_timesteps - j - 1)
                y_orig[:, j, 0] = train_val_test[self._orig_returns_col].shift(target_timesteps - j - 1)
                vol[:, j, 0] = train_val_test[self._vol_col].shift(target_timesteps - j - 1)
                
            # train/val/test split
            # note that there is overlap equal to self._timesteps between folds
            train_idx = train_val_test.loc[:start, 'idx']
            val_idx = train_val_test.loc[start+offset_delta:start+val_delta, 'idx']
            test_idx = train_val_test.loc[start+val_delta+offset_delta:start+val_delta+test_delta, 'idx']
            
            val_dt = train_val_test.loc[train_val_test['idx'].isin(val_idx)].index
            test_dt = train_val_test.loc[train_val_test['idx'].isin(test_idx)].index
            test_datetimes.append(test_dt)
            
            X_train_, y_train_, y_train_orig_, vol_train_ = \
                                X[train_idx], y[train_idx], y_orig[train_idx], vol[train_idx]
            X_val_, y_val_, y_val_orig_, vol_val_ = \
                                X[val_idx], y[val_idx], y_orig[val_idx], vol[val_idx]
            
            X_test_, y_test_, y_test_orig_, vol_test_ = \
                                X[test_idx], y[test_idx], y_orig[test_idx], vol[test_idx]
            
            # remove nan samples after applying pd.Series.shift
            X_train_ = X_train_[self._timesteps:]
            y_train_ = y_train_[self._timesteps:]
            y_train_orig_ = y_train_orig_[self._timesteps:]
            vol_train_ = vol_train_[self._timesteps:]
            
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
            
            # remove auxiliary data
            self._data[key] = self._data[key].drop(['idx'], axis=1)
            
        arrays = [X_train, X_val, X_test, y_train, y_val, y_test, y_train_orig, y_val_orig, y_test_orig, 
                  vol_train, vol_val, vol_test]
            
        def _to_tensor(x):
            x = np.concatenate(x, axis=2)
            x = torch.Tensor(x)
            return x
        
        for i in range(len(arrays)):
            arrays[i] = _to_tensor(arrays[i])
        
        
        X_train, X_val, X_test, y_train, y_val, y_test, y_train_orig, y_val_orig, y_test_orig, \
                  vol_train, vol_val, vol_test = arrays
        
        # optionally create categorical data tensors
        if self._cat_cols:
            X_cat = np.zeros((len(train_val_test), self._timesteps, len(self._cat_cols)))
            
            for i, col in enumerate(self._cat_cols):
                for j in range(self._timesteps):
                    X_cat[:, j, i] = train_val_test[col].shift(self._timesteps - j - 1)
            
            X_train_cat, X_val_cat, X_test_cat =\
                torch.Tensor(X_cat[train_idx]), torch.Tensor(X_cat[val_idx]), torch.Tensor(X_cat[test_idx])
            
            X_train_cat = X_train_cat[self._timesteps:]
            
        #check alignment by time axis
        for i in range(1, len(test_datetimes)):
            assert np.all((test_datetimes[i] - test_datetimes[0]) == pd.Timedelta(0))
        assert len(X_test) == len(test_datetimes[0]) 
        
        # fix batches sampling order for reproducibility
        g = torch.Generator()
        g.manual_seed(seed)
        
        if self._encoder_length is None:
            # dataloaders for non tft models
            if self._cat_cols:
                # note that categorical variables should be scaled in case of big absolute maximum values
                X_train = torch.cat([X_train, X_train_cat], dim=2)
                X_val = torch.cat([X_val, X_val_cat], dim=2)
                X_test = torch.cat([X_test, X_test_cat], dim=2)
            
            cat_info = {}
            
            train_loader = DataLoader(TensorDataset(X_train, y_train, y_train_orig, vol_train),
                                  shuffle=True, batch_size=self._batch_size,
                                 worker_init_fn=seed_worker, generator=g)
            val_loader = DataLoader(TensorDataset(X_val, y_val, y_val_orig, vol_val),
                                    shuffle=False, batch_size=self._batch_size)
            test_loader = DataLoader(TensorDataset(X_test, y_test, y_test_orig, vol_test),
                                     shuffle=False, batch_size=self._batch_size)
        else:
            # in case of tft model, input tensor should be split into encoder and decoder parts
            def _split_encoder_decoder(x, t):
                x_enc = x[:, :t, :]
                x_dec = x[:, t:, :]

                x_enc_length = torch.ones(len(x)).long()
                x_enc_length.fill_(x_enc.shape[1])
                x_dec_length = torch.ones(len(x)).long()
                x_dec_length.fill_(x_dec.shape[1])
            
                return x_enc, x_dec, x_enc_length, x_dec_length
            
            
            X_train_enc_real, X_train_dec_real, X_train_enc_len, X_train_dec_len =\
                _split_encoder_decoder(X_train, self._encoder_length)
            
            X_val_enc_real, X_val_dec_real, X_val_enc_len, X_val_dec_len =\
                _split_encoder_decoder(X_val, self._encoder_length)
            
            X_test_enc_real, X_test_dec_real, X_test_enc_len, X_test_dec_len =\
                _split_encoder_decoder(X_test, self._encoder_length)
            
            
            if not self._cat_cols:
                # if no categorical features are used, create dummy tensors for tft categorical inputs
                X_train_cat = torch.zeros_like(X_train).long()
                X_val_cat = torch.zeros_like(X_val).long()
                X_test_cat = torch.zeros_like(X_test).long()
            else:
                X_train_cat = X_train_cat.long()
                X_val_cat = X_val_cat.long()
                X_test_cat = X_test_cat.long()
            
            X_train_enc_cat, X_train_dec_cat, _, _ =\
                _split_encoder_decoder(X_train_cat, self._encoder_length)
            
            X_val_enc_cat, X_val_dec_cat, _, _ =\
                _split_encoder_decoder(X_val_cat, self._encoder_length)
            
            X_test_enc_cat, X_test_dec_cat, _, _ =\
                _split_encoder_decoder(X_test_cat, self._encoder_length)
            
            
            
            train_loader = DataLoader(TensorDataset(X_train_enc_real, X_train_enc_cat,
                                                    X_train_dec_real, X_train_dec_cat,
                                                    X_train_enc_len, X_train_dec_len,
                                                    y_train, y_train_orig, vol_train),
                                                    shuffle=True, batch_size=self._batch_size,
                                                    worker_init_fn=seed_worker, generator=g)
            
            val_loader = DataLoader(TensorDataset(X_val_enc_real, X_val_enc_cat,
                                                  X_val_dec_real, X_val_dec_cat,
                                                  X_val_enc_len, X_val_dec_len,
                                                  y_val, y_val_orig, vol_val),
                                                  shuffle=False, batch_size=self._batch_size)
            
            test_loader = DataLoader(TensorDataset(X_test_enc_real, X_test_enc_cat,
                                                   X_test_dec_real, X_test_dec_cat,
                                                   X_test_enc_len, X_test_dec_len,
                                                   y_test, y_test_orig, vol_test),
                                                   shuffle=False, batch_size=self._batch_size)
            
            # collect number of unique entries in each categorical feature
            if self._cat_cols:
                cat_info = {i: len(torch.unique(X_train_enc_cat[..., i])) \
                            for i in range(len(self._cat_cols))}
            else:
                cat_info = {}

                
        return train_loader, val_loader, test_loader, test_datetimes[0], cat_info
    