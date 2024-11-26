# src/application/managers/model_managers/model_manager.py
import os
import pickle
from typing import Any, Dict, Type
import numpy as np


class ModelManager:
    def __init__(self):
        self.model = None

    def train_model(self, model_class: Type[Any], X: np.ndarray, y: np.ndarray, **model_params) -> None:
        """
        Train the model with the specified model class and parameters.

        :param model_class: The class of the model to instantiate (e.g., sklearn, LightGBM, etc.).
        :param X: Training features.
        :param y: Training labels.
        :param model_params: Additional parameters for the model.
        """
        # Instantiate the model
        self.model = model_class(**model_params)
        
        # Train the model
        self.model.fit(X, y)
        print(f"Model {model_class.__name__} trained successfully with parameters: {model_params}")

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Generate predictions using the trained model.

        :param X: Features to predict.
        :return: Predictions.
        """
        if self.model is None:
            raise ValueError("Model is not trained or loaded.")
        return self.model.predict(X)

    def save_model(self, model_id: str, directory: str = "./models") -> None:
        """
        Save the model to a specified directory.

        :param model_id: Unique identifier for the model.
        :param directory: Directory to save the model.
        """
        os.makedirs(directory, exist_ok=True)
        model_path = os.path.join(directory, f"{model_id}.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)
        print(f"Model saved to {model_path}")

    def load_model(self, model_id: str, directory: str = "./models") -> None:
        """
        Load the model from a specified directory.

        :param model_id: Unique identifier for the model.
        :param directory: Directory where the model is stored.
        """
        model_path = os.path.join(directory, f"{model_id}.pkl")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file {model_path} does not exist.")
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        print(f"Model loaded from {model_path}")
