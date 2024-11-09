# src/application/managers/model_managers/lightgbm_model_manager.py
import os
import joblib
import lightgbm as lgb
from .model_manager import ModelManager

class LightGBMModelManager(ModelManager):
    def __init__(self, model_type: str = 'classifier', **kwargs):
        super().__init__()
        self.model = lgb.LGBMClassifier(**kwargs) if model_type == 'classifier' else lgb.LGBMRegressor(**kwargs)
    
    def train_model(self, X, y):
        self.model.fit(X, y)
        self.logger.info(f"LightGBM model trained on {len(X)} samples.")

    def predict(self, X):
        return self.model.predict(X)

    def save_model(self, model_id: str, directory: str = "./models"):
        os.makedirs(directory, exist_ok=True)
        model_path = os.path.join(directory, f"{model_id}_lightgbm.model")
        joblib.dump(self.model, model_path)
        self.logger.info(f"LightGBM model saved to {model_path}")

    def load_model(self, model_id: str, directory: str = "./models"):
        model_path = os.path.join(directory, f"{model_id}_lightgbm.model")
        self.model = joblib.load(model_path)
        self.logger.info(f"LightGBM model loaded from {model_path}")
