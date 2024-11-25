# src/application/managers/model_managers/model_manager.py
import os
import pickle
from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd

class ModelManager(ABC):
    def __init__(self):
        self.model = None

    @abstractmethod
    def train_model(self, X: np.ndarray, y: np.ndarray, **kwargs) -> None:
        """
        Train the model.
        """
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Generate predictions.
        """
        pass

    def save_model(self, model_id: str, directory: str = "./models") -> None:
        """
        Save the model to a specified directory.
        """
        os.makedirs(directory, exist_ok=True)
        model_path = os.path.join(directory, f"{model_id}.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)
        print(f"Model saved to {model_path}")

    def load_model(self, model_id: str, directory: str = "./models") -> None:
        """
        Load the model from a specified directory.
        """
        model_path = os.path.join(directory, f"{model_id}.pkl")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file {model_path} does not exist.")
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        print(f"Model loaded from {model_path}")
