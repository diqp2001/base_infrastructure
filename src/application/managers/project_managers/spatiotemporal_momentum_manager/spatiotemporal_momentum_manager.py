import os
from application.managers.data_managers.machine_learning.multivariate_train_val_test_splitter import MultivariateTrainValTestSplitter
from application.managers.data_managers.machine_learning.univariate_train_val_test_splitter import UnivariateTrainValTestSplitter
from application.managers.model_managers.mlp_model.mlp_model_manager import MLPModelManager
from src.application.managers.data_managers.data_manager import DataManager
from src.application.managers.model_managers.model_manager import ModelManager
from application.managers.database_managers.database_manager import DatabaseManager
from src.application.managers.model_managers.tft_model_manager import TFTModelManager
from src.application.managers.data_managers.data_manager_price import DataManagerPrice

import pandas as pd
from typing import Dict

class SpatioTemporalMomentumManager:
    def __init__(self, database_manager: DatabaseManager, data_manager: DataManagerPrice, model_manager: TFTModelManager):
        self.database_manager = database_manager
        self.data_manager = data_manager
        self.model_manager = model_manager

    def load_data(self) -> pd.DataFrame:
        """
        Load data from the database.
        """
        # Example: Load data from the database
        #data = self.database_manager.load_data("your_query_here")
        data = self.database_manager.excel_to_dataframe(file_path='Data.xlsx',index_col='Dates')
        return data

    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess the data.
        """
        assets_data = {}
        for asset_column_return in data.columns:
            preprocessed_data = self.data_manager.preprocess(data, column_name= asset_column_return)
            df, features, target = self.prepare_training_data(preprocessed_data, column_name= asset_column_return)
            asset_data = pd.concat([features, target], axis=1)
            asset_data = asset_data.dropna()
            assets_data[asset_column_return] = asset_data


        return assets_data
    
    def preprocess_data(self, data: pd.DataFrame, column_name: str) -> pd.DataFrame:
        """
        Preprocess the data.
        """
        preprocessed_data = self.data_manager.preprocess(data= data, column_name= column_name)
        return preprocessed_data

    def feature_engineering(self, data: pd.DataFrame, column_name: str, freq: int=1) -> pd.DataFrame:
        """
        Perform feature engineering.
        """
        data = data [[column_name]]
        # Add Deep Momentum features
        data = self.data_manager.add_deep_momentum_features(data=data, column_name=column_name)

        # Add MACD features
        data = self.data_manager.add_macd_signal_features(data=data, column_name=column_name)

        

        return data

    def prepare_training_data(self, data: pd.DataFrame, column_name: str = 'price close') -> tuple:
        """
        Prepare data for machine learning training.
        """
        # Perform feature engineering
        data = self.feature_engineering(data, column_name=column_name)

        data, target_column_name = self.data_manager.add_target(data=data, column_name=column_name, freq=1)
        data, target_non_scaled_column_name = self.data_manager.add_target_non_scaled(data=data, column_name=column_name, freq=1)
        target = data[[target_column_name,target_non_scaled_column_name]]
        features = data.drop(columns=[target_column_name,target_non_scaled_column_name,column_name])

        return data, features, target

    def train_models(self, data: pd.DataFrame) -> None:
        """
        Train models
        """
        m_results = {}

        results = self.train_model_mlp_univariate(data=data)
        m_results['mlp']
        return m_results

    def evaluate_models(self, data: pd.DataFrame):
        """
        Evaluate the TFT model.
        """
        evaluation_results = self.model_manager.evaluate(self.model_manager.model, data)
        return evaluation_results
    
    def create_multivariate_tensors(self, data: pd.DataFrame, cols, cat_cols, target_col, orig_returns_col, vol_col, timesteps=63,scaling=None, batch_size=64, encoder_length=None):
        splitter = MultivariateTrainValTestSplitter(data, cols,cat_cols, target_col,
                                                orig_returns_col, vol_col,
                                                 timesteps,scaling,batch_size,
                                                 encoder_length)
        return splitter
    
    def create_univariate_tensors(self, data: pd.DataFrame, cols, cat_cols, target_col, orig_returns_col, vol_col, timesteps=63,scaling=None, encoder_length=None):
        for asset in data.keys():
            data[asset]['asset'] = asset
        splitter = UnivariateTrainValTestSplitter(data, cols, cat_cols, target_col, orig_returns_col, vol_col, scaling=scaling, timesteps= timesteps, encoder_length=encoder_length, use_asset_info_as_feature= False)
        return splitter
    
    def train_model_mlp_univariate(self, data: pd.DataFrame):
        self.model_manager = MLPModelManager()
        val_delta = pd.Timedelta('365days')
        test_delta = pd.Timedelta('365days')
        date_range = pd.date_range('2017-01-01','2020-12-31',freq='365d')
        cols_to_use = [
            'norm_daily_return',
            'norm_monthly_return',
            'norm_quarterly_return',
            'norm_biannual_return',
            'norm_annual_return',
            'macd_8_24',
            'macd_16_48',
            'macd_32_96',
        ]
        datetime_cols = None
        model_type = 'mlp'
        scaling = None #'standard', 'minmax'
        
        if model_type == 'tft':
            history_size = 63
            encoder_length = 42 # in case of tft encoder length should be int
            model_params = {'device': 'cuda'}
            use_asset_info_as_feature = True # use asset name as categorical variable
        else:
            history_size = 21
            encoder_length = None # in case of non tft model encoder length should be None
            model_params = {}
            use_asset_info_as_feature = False

        results = {}

        splitter = self.create_univariate_tensors(data,cols_to_use,datetime_cols,'target_returns','target_returns_nonscaled','daily_vol',scaling=scaling, timesteps=history_size, encoder_length=encoder_length)
        for seed in [42]:
            if not os.path.exists('weights'):
                os.mkdir('weights')
            if not os.path.exists('results'):
                os.mkidr('results')
            for start in date_range:
                test_dt,val_preds,val_returns,val_vols,test_preds,test_returns,test_vols = self.model_manager.train_univariate( splitter, start, val_delta, test_delta, seed)
                dt = start
                results[dt] = {}

                results[dt]['val'] = {}
                results[dt]['test'] = {}
                results[dt]['test_dt'] = test_dt

                results[dt]['val']['preds'] = val_preds
                results[dt]['val']['returns'] = val_returns
                results[dt]['val']['vols'] = val_vols

                results[dt]['test']['preds']  = test_preds
                results[dt]['test']['returns'] = test_returns
                results[dt]['test']['vols'] = test_vols

        return results

    def run(self, target_column: str = 'price close'):
        """
        Run the entire pipeline.
        """
        data = self.load_data()
        data = self.prepare_features(data)
        m_results = self.train_models(data)
        self.evaluate_models(m_results)
        