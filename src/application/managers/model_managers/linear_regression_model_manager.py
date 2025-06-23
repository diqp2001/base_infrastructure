import pickle
import pandas as pd
import numpy as np
from typing import Dict, Any
from sklearn.linear_model import LinearRegression
from src.application.managers.model_managers.model_manager import ModelManager

class LinearRegressionModelManager(ModelManager):
    def __init__(self, target_column: str = 'price close'):
        super().__init__()
        self.model = LinearRegression()
        self.target_column = target_column

    def train(self, features: pd.DataFrame, target: pd.Series) -> None:
        """
        Train the Linear Regression model.
        """
        self.model.fit(features, target)

    def evaluate(self, model: Any, test_data: pd.DataFrame) -> Dict[str, float]:
        """
        Evaluate the Linear Regression model.
        """
        X_test = test_data.drop(columns=[self.target_column])
        y_test = test_data[self.target_column]
        y_pred = model.predict(X_test)
        mse = np.mean((y_pred - y_test) ** 2)
        return {"MSE": mse}