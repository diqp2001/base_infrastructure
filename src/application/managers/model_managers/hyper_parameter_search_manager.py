from typing import Any, Dict, Tuple
import numpy as np
import optuna
from sklearn.model_selection import RandomizedSearchCV, cross_val_score

class HyperparameterSearchManager:
    def __init__(self, search_method: str = "optuna", n_trials: int = 50, random_seed: int = 42):
        """
        Initialize the hyperparameter search manager.
        
        :param search_method: The optimization method ('optuna' or 'random_search').
        :param n_trials: Number of trials for Optuna (ignored for random search).
        :param random_seed: Seed for reproducibility.
        """
        self.search_method = search_method
        self.n_trials = n_trials
        self.random_seed = random_seed

    def optimize(
        self, 
        model_class: Any, 
        X_train: np.ndarray, 
        y_train: np.ndarray, 
        param_distributions: Dict, 
        scoring: str = "accuracy", 
        cv: int = 3
    ) -> Tuple[Dict, Any]:
        """
        Perform hyperparameter search.
        
        :param model_class: Model class (e.g., LGBMClassifier, RandomForestClassifier).
        :param X_train: Training features.
        :param y_train: Training labels.
        :param param_distributions: Dictionary of hyperparameter distributions.
        :param scoring: Metric to optimize.
        :param cv: Number of cross-validation folds.
        :return: Best parameters and trained model.
        """
        if self.search_method == "optuna":
            def objective(trial):
                params = {
                    key: trial.suggest_categorical(key, values) if isinstance(values, list)
                    else trial.suggest_float(key, values[0], values[1]) 
                    for key, values in param_distributions.items()
                }
                model = model_class(**params)
                model.fit(X_train, y_train)
                score = np.mean(cross_val_score(model, X_train, y_train, cv=cv, scoring=scoring))
                return score

            study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=self.random_seed))
            study.optimize(objective, n_trials=self.n_trials)
            best_params = study.best_params
            best_model = model_class(**best_params)
            best_model.fit(X_train, y_train)
            return best_params, best_model

        elif self.search_method == "random_search":
            model = model_class()
            search = RandomizedSearchCV(
                estimator=model, 
                param_distributions=param_distributions, 
                scoring=scoring, 
                cv=cv, 
                random_state=self.random_seed, 
                n_iter=self.n_trials
            )
            search.fit(X_train, y_train)
            return search.best_params_, search.best_estimator_

        else:
            raise ValueError(f"Unknown search method: {self.search_method}")
