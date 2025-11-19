# src/application/services/model_service.py
import os
import pickle
import joblib
import json
from typing import Any, Dict, Type, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, regression_report
from src.application.services.database_service import DatabaseService


class ModelService:
    """Service class for managing machine learning models, training, evaluation, and persistence."""
    
    def __init__(self, db_type: str = 'sqlite', models_directory: str = "./models"):
        """
        Initialize the ModelService.
        :param db_type: Database type for DatabaseService.
        :param models_directory: Directory to store model files.
        """
        self.database_service = DatabaseService(db_type)
        self.models_directory = models_directory
        self.current_model = None
        self.model_metadata = {}
        
        # Create models directory if it doesn't exist
        os.makedirs(models_directory, exist_ok=True)
    
    def train_model(self, model_class: Type[Any], X: np.ndarray, y: np.ndarray, 
                   model_id: str = None, validation_split: float = 0.2, 
                   **model_params) -> Dict[str, Any]:
        """
        Train a model with the specified class and parameters.
        :param model_class: The class of the model to instantiate.
        :param X: Training features.
        :param y: Training labels/targets.
        :param model_id: Optional unique identifier for the model.
        :param validation_split: Fraction of data to use for validation.
        :param model_params: Additional parameters for the model.
        :return: Training results dictionary.
        """
        try:
            # Generate model ID if not provided
            if model_id is None:
                model_id = f"{model_class.__name__}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Split data for validation
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=validation_split, random_state=42
            )
            
            # Instantiate and train the model
            self.current_model = model_class(**model_params)
            self.current_model.fit(X_train, y_train)
            
            # Evaluate the model
            train_score = self.current_model.score(X_train, y_train)
            val_score = self.current_model.score(X_val, y_val)
            
            # Store model metadata
            self.model_metadata = {
                'model_id': model_id,
                'model_class': model_class.__name__,
                'model_params': model_params,
                'training_samples': len(X_train),
                'validation_samples': len(X_val),
                'feature_count': X.shape[1] if len(X.shape) > 1 else 1,
                'train_score': train_score,
                'validation_score': val_score,
                'training_date': datetime.now().isoformat(),
                'status': 'trained'
            }
            
            # Save model metadata to database
            self._save_model_metadata(self.model_metadata)
            
            results = {
                'model_id': model_id,
                'train_score': train_score,
                'validation_score': val_score,
                'model_class': model_class.__name__,
                'training_samples': len(X_train),
                'validation_samples': len(X_val)
            }
            
            print(f"Model {model_class.__name__} (ID: {model_id}) trained successfully")
            print(f"Train Score: {train_score:.4f}, Validation Score: {val_score:.4f}")
            
            return results
            
        except Exception as e:
            print(f"Error training model: {e}")
            return {}
    
    def cross_validate_model(self, model_class: Type[Any], X: np.ndarray, y: np.ndarray,
                           cv_folds: int = 5, scoring: str = None, **model_params) -> Dict[str, Any]:
        """
        Perform cross-validation on a model.
        :param model_class: The class of the model to validate.
        :param X: Features.
        :param y: Labels/targets.
        :param cv_folds: Number of cross-validation folds.
        :param scoring: Scoring method for cross-validation.
        :param model_params: Model parameters.
        :return: Cross-validation results.
        """
        try:
            model = model_class(**model_params)
            scores = cross_val_score(model, X, y, cv=cv_folds, scoring=scoring)
            
            results = {
                'model_class': model_class.__name__,
                'cv_scores': scores.tolist(),
                'mean_score': scores.mean(),
                'std_score': scores.std(),
                'cv_folds': cv_folds,
                'scoring': scoring or 'default'
            }
            
            print(f"Cross-validation results for {model_class.__name__}:")
            print(f"Mean Score: {results['mean_score']:.4f} (+/- {results['std_score']*2:.4f})")
            
            return results
            
        except Exception as e:
            print(f"Error in cross-validation: {e}")
            return {}
    
    def predict(self, X: np.ndarray, model_id: str = None) -> np.ndarray:
        """
        Generate predictions using the current or specified model.
        :param X: Features to predict.
        :param model_id: Optional model ID to load specific model.
        :return: Predictions.
        """
        try:
            if model_id and model_id != self.model_metadata.get('model_id'):
                self.load_model(model_id)
            
            if self.current_model is None:
                raise ValueError("No model is loaded. Please train or load a model first.")
            
            predictions = self.current_model.predict(X)
            print(f"Generated {len(predictions)} predictions")
            return predictions
            
        except Exception as e:
            print(f"Error making predictions: {e}")
            return np.array([])
    
    def predict_proba(self, X: np.ndarray, model_id: str = None) -> np.ndarray:
        """
        Generate probability predictions (for classification models).
        :param X: Features to predict.
        :param model_id: Optional model ID to load specific model.
        :return: Prediction probabilities.
        """
        try:
            if model_id and model_id != self.model_metadata.get('model_id'):
                self.load_model(model_id)
            
            if self.current_model is None:
                raise ValueError("No model is loaded. Please train or load a model first.")
            
            if not hasattr(self.current_model, 'predict_proba'):
                raise ValueError("Model does not support probability predictions")
            
            probabilities = self.current_model.predict_proba(X)
            return probabilities
            
        except Exception as e:
            print(f"Error making probability predictions: {e}")
            return np.array([])
    
    def evaluate_model(self, X_test: np.ndarray, y_test: np.ndarray, 
                      model_id: str = None, task_type: str = 'auto') -> Dict[str, Any]:
        """
        Evaluate model performance on test data.
        :param X_test: Test features.
        :param y_test: Test labels/targets.
        :param model_id: Optional model ID to load specific model.
        :param task_type: Type of task ('classification', 'regression', 'auto').
        :return: Evaluation results.
        """
        try:
            if model_id and model_id != self.model_metadata.get('model_id'):
                self.load_model(model_id)
            
            if self.current_model is None:
                raise ValueError("No model is loaded. Please train or load a model first.")
            
            # Make predictions
            y_pred = self.current_model.predict(X_test)
            
            # Determine task type
            if task_type == 'auto':
                task_type = self._determine_task_type(y_test)
            
            results = {
                'model_id': self.model_metadata.get('model_id', 'unknown'),
                'task_type': task_type,
                'test_samples': len(X_test),
                'evaluation_date': datetime.now().isoformat()
            }
            
            if task_type == 'classification':
                from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
                
                results.update({
                    'accuracy': accuracy_score(y_test, y_pred),
                    'precision': precision_score(y_test, y_pred, average='weighted'),
                    'recall': recall_score(y_test, y_pred, average='weighted'),
                    'f1_score': f1_score(y_test, y_pred, average='weighted')
                })
                
                # Add classification report if possible
                try:
                    results['classification_report'] = classification_report(y_test, y_pred, output_dict=True)
                except:
                    pass
                
            elif task_type == 'regression':
                from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
                
                results.update({
                    'mse': mean_squared_error(y_test, y_pred),
                    'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
                    'mae': mean_absolute_error(y_test, y_pred),
                    'r2_score': r2_score(y_test, y_pred)
                })
            
            print(f"Model evaluation completed for {results['model_id']}")
            return results
            
        except Exception as e:
            print(f"Error evaluating model: {e}")
            return {}
    
    def save_model(self, model_id: str = None, save_format: str = 'pickle') -> bool:
        """
        Save the current model to disk.
        :param model_id: Model identifier (uses current model_id if not provided).
        :param save_format: Format to save ('pickle', 'joblib').
        :return: True if successful, False otherwise.
        """
        try:
            if self.current_model is None:
                raise ValueError("No model to save. Please train a model first.")
            
            if model_id is None:
                model_id = self.model_metadata.get('model_id', f'model_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            
            # Determine file extension based on format
            if save_format == 'pickle':
                extension = '.pkl'
                save_func = pickle.dump
            elif save_format == 'joblib':
                extension = '.joblib'
                save_func = joblib.dump
            else:
                raise ValueError(f"Unsupported save format: {save_format}")
            
            # Save model
            model_path = os.path.join(self.models_directory, f"{model_id}{extension}")
            
            if save_format == 'pickle':
                with open(model_path, 'wb') as f:
                    save_func(self.current_model, f)
            else:
                save_func(self.current_model, model_path)
            
            # Save metadata
            metadata_path = os.path.join(self.models_directory, f"{model_id}_metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(self.model_metadata, f, indent=2, default=str)
            
            # Update database record
            self._update_model_metadata(model_id, {'file_path': model_path, 'status': 'saved'})
            
            print(f"Model saved successfully to {model_path}")
            return True
            
        except Exception as e:
            print(f"Error saving model: {e}")
            return False
    
    def load_model(self, model_id: str, load_format: str = 'auto') -> bool:
        """
        Load a model from disk.
        :param model_id: Model identifier.
        :param load_format: Format to load ('pickle', 'joblib', 'auto').
        :return: True if successful, False otherwise.
        """
        try:
            # Auto-detect format if not specified
            if load_format == 'auto':
                pickle_path = os.path.join(self.models_directory, f"{model_id}.pkl")
                joblib_path = os.path.join(self.models_directory, f"{model_id}.joblib")
                
                if os.path.exists(pickle_path):
                    load_format = 'pickle'
                    model_path = pickle_path
                elif os.path.exists(joblib_path):
                    load_format = 'joblib'
                    model_path = joblib_path
                else:
                    raise FileNotFoundError(f"No model file found for ID: {model_id}")
            else:
                extension = '.pkl' if load_format == 'pickle' else '.joblib'
                model_path = os.path.join(self.models_directory, f"{model_id}{extension}")
            
            # Load model
            if load_format == 'pickle':
                with open(model_path, 'rb') as f:
                    self.current_model = pickle.load(f)
            elif load_format == 'joblib':
                self.current_model = joblib.load(model_path)
            
            # Load metadata
            metadata_path = os.path.join(self.models_directory, f"{model_id}_metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    self.model_metadata = json.load(f)
            else:
                # Try to get from database
                self.model_metadata = self._get_model_metadata(model_id) or {}
            
            print(f"Model {model_id} loaded successfully")
            return True
            
        except Exception as e:
            print(f"Error loading model {model_id}: {e}")
            return False
    
    def list_models(self, status: str = None) -> List[Dict[str, Any]]:
        """
        List all saved models.
        :param status: Optional status filter.
        :return: List of model information dictionaries.
        """
        try:
            query = "SELECT * FROM model_metadata"
            params = {}
            
            if status:
                query += " WHERE status = :status"
                params['status'] = status
            
            result = self.database_service.session.execute(query, params).fetchall()
            return [dict(row) for row in result]
            
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
    
    def delete_model(self, model_id: str) -> bool:
        """
        Delete a model from disk and database.
        :param model_id: Model identifier.
        :return: True if successful, False otherwise.
        """
        try:
            # Delete model files
            for extension in ['.pkl', '.joblib']:
                model_path = os.path.join(self.models_directory, f"{model_id}{extension}")
                if os.path.exists(model_path):
                    os.remove(model_path)
            
            # Delete metadata file
            metadata_path = os.path.join(self.models_directory, f"{model_id}_metadata.json")
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
            
            # Delete from database
            self.database_service.session.execute(
                "DELETE FROM model_metadata WHERE model_id = :model_id",
                {'model_id': model_id}
            )
            self.database_service.session.commit()
            
            print(f"Model {model_id} deleted successfully")
            return True
            
        except Exception as e:
            print(f"Error deleting model {model_id}: {e}")
            return False
    
    def compare_models(self, model_ids: List[str], X_test: np.ndarray, 
                      y_test: np.ndarray) -> pd.DataFrame:
        """
        Compare performance of multiple models.
        :param model_ids: List of model IDs to compare.
        :param X_test: Test features.
        :param y_test: Test labels/targets.
        :return: DataFrame with comparison results.
        """
        comparison_results = []
        
        for model_id in model_ids:
            try:
                self.load_model(model_id)
                results = self.evaluate_model(X_test, y_test, task_type='auto')
                
                if results:
                    comparison_results.append({
                        'model_id': model_id,
                        'model_class': self.model_metadata.get('model_class', 'unknown'),
                        **results
                    })
            except Exception as e:
                print(f"Error evaluating model {model_id}: {e}")
        
        return pd.DataFrame(comparison_results)
    
    def get_feature_importance(self, feature_names: List[str] = None) -> Optional[Dict[str, float]]:
        """
        Get feature importance from the current model.
        :param feature_names: Optional list of feature names.
        :return: Dictionary of feature importance or None.
        """
        try:
            if self.current_model is None:
                raise ValueError("No model is loaded")
            
            if hasattr(self.current_model, 'feature_importances_'):
                importance = self.current_model.feature_importances_
                
                if feature_names and len(feature_names) == len(importance):
                    return dict(zip(feature_names, importance))
                else:
                    return {f'feature_{i}': imp for i, imp in enumerate(importance)}
            
            elif hasattr(self.current_model, 'coef_'):
                # For linear models
                coef = np.abs(self.current_model.coef_.flatten())
                
                if feature_names and len(feature_names) == len(coef):
                    return dict(zip(feature_names, coef))
                else:
                    return {f'feature_{i}': c for i, c in enumerate(coef)}
            
            else:
                print("Model does not provide feature importance")
                return None
            
        except Exception as e:
            print(f"Error getting feature importance: {e}")
            return None
    
    def _determine_task_type(self, y: np.ndarray) -> str:
        """Determine if task is classification or regression based on target values."""
        if len(np.unique(y)) < 20 and np.all(y == y.astype(int)):
            return 'classification'
        else:
            return 'regression'
    
    def _save_model_metadata(self, metadata: Dict[str, Any]):
        """Save model metadata to database."""
        try:
            # Create table if not exists
            create_table_query = """
            CREATE TABLE IF NOT EXISTS model_metadata (
                model_id TEXT PRIMARY KEY,
                model_class TEXT,
                model_params TEXT,
                training_samples INTEGER,
                validation_samples INTEGER,
                feature_count INTEGER,
                train_score REAL,
                validation_score REAL,
                training_date TEXT,
                status TEXT,
                file_path TEXT
            )
            """
            self.database_service.session.execute(create_table_query)
            
            # Insert metadata
            insert_query = """
            INSERT OR REPLACE INTO model_metadata 
            (model_id, model_class, model_params, training_samples, validation_samples,
             feature_count, train_score, validation_score, training_date, status)
            VALUES (:model_id, :model_class, :model_params, :training_samples, :validation_samples,
                    :feature_count, :train_score, :validation_score, :training_date, :status)
            """
            
            self.database_service.session.execute(insert_query, {
                **metadata,
                'model_params': json.dumps(metadata.get('model_params', {}))
            })
            self.database_service.session.commit()
            
        except Exception as e:
            print(f"Error saving model metadata: {e}")
    
    def _update_model_metadata(self, model_id: str, updates: Dict[str, Any]):
        """Update model metadata in database."""
        try:
            set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
            query = f"UPDATE model_metadata SET {set_clause} WHERE model_id = :model_id"
            
            params = {**updates, 'model_id': model_id}
            self.database_service.session.execute(query, params)
            self.database_service.session.commit()
            
        except Exception as e:
            print(f"Error updating model metadata: {e}")
    
    def _get_model_metadata(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model metadata from database."""
        try:
            query = "SELECT * FROM model_metadata WHERE model_id = :model_id"
            result = self.database_service.session.execute(query, {'model_id': model_id}).fetchone()
            
            if result:
                metadata = dict(result)
                # Parse JSON fields
                if 'model_params' in metadata:
                    try:
                        metadata['model_params'] = json.loads(metadata['model_params'])
                    except:
                        pass
                return metadata
            return None
            
        except Exception as e:
            print(f"Error getting model metadata: {e}")
            return None