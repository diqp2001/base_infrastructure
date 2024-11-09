# src/application/managers/model_managers/scikit_learn_model_manager.py
import os
import joblib
from sklearn.ensemble import RandomForestClassifier
from .model_manager import ModelManager

class ScikitLearnModelManager(ModelManager):
    def __init__(self, **kwargs):
        super().__init__()
        self.model = RandomForestClassifier(**kwargs)
    
    def train_model(self, X, y):
        self.model.fit(X, y)
        self.logger.info("Scikit-Learn model trained.")

    def predict(self, X):
        return self.model.predict(X)

    def save_model(self, model_id: str, directory: str = "./models"):
        os.makedirs(directory, exist_ok=True)
        model_path = os.path.join(directory, f"{model_id}_sklearn.model")
        joblib.dump(self.model, model_path)
        self.logger.info(f"Scikit-Learn model saved to {model_path}")

    def load_model(self, model_id: str, directory: str = "./models"):
        model_path = os.path.join(directory, f"{model_id}_sklearn.model")
        self.model = joblib.load(model_path)
        self.logger.info(f"Scikit-Learn model loaded from {model_path}")
