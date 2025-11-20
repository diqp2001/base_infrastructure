import pickle
import pandas as pd
import numpy as np
from typing import Dict, Any
from sklearn.ensemble import RandomForestRegressor
from application.services.model_service.model_service import ModelService

class RandomForestModelService(ModelService):
    """Random Forest Model Service - ensemble learning service for robust predictions using multiple decision trees."""
    
    def __init__(self, target_column: str = 'price close', n_estimators: int = 100):
        super().__init__()
        self.model = RandomForestRegressor(n_estimators=n_estimators)
        self.target_column = target_column

    def train_model(self, features: pd.DataFrame, target: pd.Series) -> None:
        """
        Train the Random Forest model.
        """
        self.model.fit(features, target)

    def evaluate_model(self, model: Any, test_data: pd.DataFrame) -> Dict[str, float]:
        """
        Evaluate the Random Forest model.
        """
        X_test = test_data.drop(columns=[self.target_column])
        y_test = test_data[self.target_column]
        y_pred = model.predict(X_test)
        mse = np.mean((y_pred - y_test) ** 2)
        return {"MSE": mse}