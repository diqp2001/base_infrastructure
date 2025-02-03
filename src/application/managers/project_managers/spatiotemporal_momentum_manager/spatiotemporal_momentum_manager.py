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
        data = self.database_manager.load_data("your_query_here")
        return data

    def preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess the data.
        """
        preprocessed_data = self.data_manager.preprocess(data)
        return preprocessed_data

    def feature_engineering(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Perform feature engineering.
        """
        # Add Deep Momentum features
        data = self.data_manager.add_deep_momentum_features(data)

        # Add MACD features
        data = self.data_manager.add_macd_features(data)

        # Drop rows with NaN values created by feature engineering
        data = data.dropna()

        return data

    def prepare_training_data(self, data: pd.DataFrame, target_column: str = 'price close') -> tuple:
        """
        Prepare data for machine learning training.
        """
        # Perform feature engineering
        features = self.feature_engineering(data)

        # Separate features and target
        target = features[target_column]
        features = features.drop(columns=[target_column])

        return features, target

    def train_model(self, features: pd.DataFrame, target: pd.Series) -> None:
        """
        Train the TFT model.
        """
        self.model_manager.train(features, target)

    def evaluate_model(self, test_data: pd.DataFrame) -> Dict[str, float]:
        """
        Evaluate the TFT model.
        """
        evaluation_results = self.model_manager.evaluate(self.model_manager.model, test_data)
        return evaluation_results

    def save_model(self, filepath: str) -> None:
        """
        Save the trained model.
        """
        self.model_manager.save_model(self.model_manager.model, filepath)

    def run(self, target_column: str = 'price close'):
        """
        Run the entire pipeline.
        """
        data = self.load_data()
        preprocessed_data = self.preprocess_data(data)
        features, target = self.prepare_training_data(preprocessed_data, target_column)
        self.train_model(features, target)
        evaluation_results = self.evaluate_model(preprocessed_data)
        self.save_model("tft_model.pkl")
        return evaluation_results