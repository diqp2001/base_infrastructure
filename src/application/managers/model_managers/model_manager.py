# src/application/managers/model_managers/model_manager.py

import os
from src.application.managers.manager import Manager

class ModelManager(Manager):
    def __init__(self):
        super().__init__()
        self.model = None
    
    def save_model(self, model_id: str, directory: str = "./models"):
        """
        Save model to specified directory. To be implemented by each subclass.
        """
        raise NotImplementedError("Each model manager must implement its save_model method.")

    def load_model(self, model_id: str, directory: str = "./models"):
        """
        Load model from specified directory. To be implemented by each subclass.
        """
        raise NotImplementedError("Each model manager must implement its load_model method.")

    def train_model(self, X, y, **kwargs):
        """
        Train model. To be implemented by each subclass.
        """
        raise NotImplementedError("Each model manager must implement its train_model method.")

    def predict(self, X):
        """
        Generate predictions. To be implemented by each subclass.
        """
        raise NotImplementedError("Each model manager must implement its predict method.")
