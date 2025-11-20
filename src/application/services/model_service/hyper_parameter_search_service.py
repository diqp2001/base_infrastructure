import itertools
import random
from typing import Dict, List, Any, Optional, Callable, Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import ParameterGrid, ParameterSampler
from sklearn.metrics import mean_squared_error, accuracy_score, f1_score, roc_auc_score
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging


class HyperParameterSearchService:
    """
    Service for hyperparameter optimization and model tuning.
    Supports grid search, random search, and Bayesian optimization strategies.
    """
    
    def __init__(self, random_seed: int = 42, n_jobs: int = 1):
        """
        Initialize the hyperparameter search service.
        
        Args:
            random_seed: Random seed for reproducibility
            n_jobs: Number of parallel jobs for search
        """
        self.random_seed = random_seed
        self.n_jobs = n_jobs
        self.results_history = []
        self.best_params = None
        self.best_score = None
        self.search_completed = False
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def grid_search(self, model_class: Any, param_grid: Dict[str, List[Any]],
                   train_data: Tuple, val_data: Tuple,
                   scoring_function: Callable = None,
                   cv_folds: int = None) -> Dict[str, Any]:
        """
        Perform grid search hyperparameter optimization.
        
        Args:
            model_class: Model class to optimize
            param_grid: Dictionary of parameter names and value lists
            train_data: Training data (X_train, y_train)
            val_data: Validation data (X_val, y_val)
            scoring_function: Function to evaluate model performance
            cv_folds: Number of cross-validation folds (optional)
            
        Returns:
            Dictionary with best parameters and results
        """
        self.logger.info(f"Starting grid search with {len(ParameterGrid(param_grid))} combinations")
        
        X_train, y_train = train_data
        X_val, y_val = val_data
        
        if scoring_function is None:
            scoring_function = self._default_scoring_function
        
        best_score = float('-inf') if self._is_maximizing_metric(scoring_function) else float('inf')
        best_params = None
        all_results = []
        
        # Generate all parameter combinations
        param_combinations = list(ParameterGrid(param_grid))
        
        # Parallel execution
        if self.n_jobs > 1:
            results = self._parallel_search(
                model_class, param_combinations, train_data, val_data,
                scoring_function, cv_folds
            )
        else:
            results = []
            for params in param_combinations:
                result = self._evaluate_params(
                    model_class, params, train_data, val_data,
                    scoring_function, cv_folds
                )
                results.append(result)
        
        # Find best result
        for result in results:
            score = result['score']
            if self._is_better_score(score, best_score, scoring_function):
                best_score = score
                best_params = result['params']
            all_results.append(result)
        
        self.best_params = best_params
        self.best_score = best_score
        self.results_history = all_results
        self.search_completed = True
        
        self.logger.info(f"Grid search completed. Best score: {best_score}")
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'all_results': all_results,
            'search_type': 'grid_search'
        }

    def random_search(self, model_class: Any, param_distributions: Dict[str, Any],
                     train_data: Tuple, val_data: Tuple,
                     n_iter: int = 10, scoring_function: Callable = None,
                     cv_folds: int = None) -> Dict[str, Any]:
        """
        Perform random search hyperparameter optimization.
        
        Args:
            model_class: Model class to optimize
            param_distributions: Dictionary of parameter distributions
            train_data: Training data (X_train, y_train)
            val_data: Validation data (X_val, y_val)
            n_iter: Number of parameter combinations to try
            scoring_function: Function to evaluate model performance
            cv_folds: Number of cross-validation folds (optional)
            
        Returns:
            Dictionary with best parameters and results
        """
        self.logger.info(f"Starting random search with {n_iter} iterations")
        
        if scoring_function is None:
            scoring_function = self._default_scoring_function
        
        best_score = float('-inf') if self._is_maximizing_metric(scoring_function) else float('inf')
        best_params = None
        all_results = []
        
        # Generate random parameter combinations
        param_sampler = ParameterSampler(
            param_distributions, n_iter=n_iter, random_state=self.random_seed
        )
        param_combinations = list(param_sampler)
        
        # Parallel execution
        if self.n_jobs > 1:
            results = self._parallel_search(
                model_class, param_combinations, train_data, val_data,
                scoring_function, cv_folds
            )
        else:
            results = []
            for params in param_combinations:
                result = self._evaluate_params(
                    model_class, params, train_data, val_data,
                    scoring_function, cv_folds
                )
                results.append(result)
        
        # Find best result
        for result in results:
            score = result['score']
            if self._is_better_score(score, best_score, scoring_function):
                best_score = score
                best_params = result['params']
            all_results.append(result)
        
        self.best_params = best_params
        self.best_score = best_score
        self.results_history = all_results
        self.search_completed = True
        
        self.logger.info(f"Random search completed. Best score: {best_score}")
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'all_results': all_results,
            'search_type': 'random_search'
        }

    def bayesian_search(self, model_class: Any, param_space: Dict[str, Any],
                       train_data: Tuple, val_data: Tuple,
                       n_calls: int = 10, scoring_function: Callable = None,
                       cv_folds: int = None) -> Dict[str, Any]:
        """
        Perform Bayesian optimization hyperparameter search.
        Note: This is a simplified implementation. For production use,
        consider using specialized libraries like scikit-optimize.
        
        Args:
            model_class: Model class to optimize
            param_space: Dictionary defining parameter search space
            train_data: Training data (X_train, y_train)
            val_data: Validation data (X_val, y_val)
            n_calls: Number of optimization calls
            scoring_function: Function to evaluate model performance
            cv_folds: Number of cross-validation folds (optional)
            
        Returns:
            Dictionary with best parameters and results
        """
        self.logger.info(f"Starting Bayesian search with {n_calls} calls")
        
        # For this simplified implementation, we'll use random sampling
        # In practice, you'd use Gaussian processes or other surrogate models
        return self.random_search(
            model_class, param_space, train_data, val_data,
            n_iter=n_calls, scoring_function=scoring_function, cv_folds=cv_folds
        )

    def _parallel_search(self, model_class: Any, param_combinations: List[Dict],
                        train_data: Tuple, val_data: Tuple,
                        scoring_function: Callable, cv_folds: int = None) -> List[Dict]:
        """Execute parameter evaluation in parallel."""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.n_jobs) as executor:
            # Submit all tasks
            future_to_params = {
                executor.submit(
                    self._evaluate_params, model_class, params, train_data,
                    val_data, scoring_function, cv_folds
                ): params
                for params in param_combinations
            }
            
            # Collect results
            for future in as_completed(future_to_params):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    params = future_to_params[future]
                    self.logger.error(f"Error evaluating params {params}: {e}")
                    results.append({
                        'params': params,
                        'score': float('-inf'),
                        'error': str(e)
                    })
        
        return results

    def _evaluate_params(self, model_class: Any, params: Dict,
                        train_data: Tuple, val_data: Tuple,
                        scoring_function: Callable, cv_folds: int = None) -> Dict[str, Any]:
        """Evaluate a single parameter combination."""
        try:
            X_train, y_train = train_data
            X_val, y_val = val_data
            
            # Create and train model
            model = model_class(**params)
            model.fit(X_train, y_train)
            
            # Make predictions
            if hasattr(model, 'predict_proba'):
                y_pred = model.predict_proba(X_val)
                if y_pred.ndim > 1 and y_pred.shape[1] > 1:
                    y_pred = y_pred[:, 1]  # Use positive class probability
            else:
                y_pred = model.predict(X_val)
            
            # Calculate score
            if cv_folds and cv_folds > 1:
                score = self._cross_validate_score(
                    model_class, params, X_train, y_train, cv_folds, scoring_function
                )
            else:
                score = scoring_function(y_val, y_pred)
            
            return {
                'params': params,
                'score': score,
                'model': model
            }
            
        except Exception as e:
            self.logger.error(f"Error evaluating params {params}: {e}")
            return {
                'params': params,
                'score': float('-inf'),
                'error': str(e)
            }

    def _cross_validate_score(self, model_class: Any, params: Dict,
                            X: np.ndarray, y: np.ndarray, cv_folds: int,
                            scoring_function: Callable) -> float:
        """Perform cross-validation scoring."""
        from sklearn.model_selection import KFold
        
        kf = KFold(n_splits=cv_folds, shuffle=True, random_state=self.random_seed)
        scores = []
        
        for train_idx, val_idx in kf.split(X):
            X_train_fold, X_val_fold = X[train_idx], X[val_idx]
            y_train_fold, y_val_fold = y[train_idx], y[val_idx]
            
            model = model_class(**params)
            model.fit(X_train_fold, y_train_fold)
            
            if hasattr(model, 'predict_proba'):
                y_pred = model.predict_proba(X_val_fold)
                if y_pred.ndim > 1 and y_pred.shape[1] > 1:
                    y_pred = y_pred[:, 1]
            else:
                y_pred = model.predict(X_val_fold)
            
            score = scoring_function(y_val_fold, y_pred)
            scores.append(score)
        
        return np.mean(scores)

    def _default_scoring_function(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Default scoring function (MSE for regression, accuracy for classification)."""
        # Determine if this is a classification or regression problem
        if len(np.unique(y_true)) <= 10 and np.all(y_true == np.round(y_true)):
            # Classification
            y_pred_class = np.round(y_pred) if y_pred.dtype == float else y_pred
            return accuracy_score(y_true, y_pred_class)
        else:
            # Regression
            return -mean_squared_error(y_true, y_pred)  # Negative for maximization

    def _is_maximizing_metric(self, scoring_function: Callable) -> bool:
        """Determine if the metric should be maximized."""
        # Check function name for common patterns
        func_name = scoring_function.__name__.lower()
        maximizing_metrics = ['accuracy', 'precision', 'recall', 'f1', 'auc', 'roc']
        minimizing_metrics = ['mse', 'mae', 'rmse', 'loss', 'error']
        
        if any(metric in func_name for metric in maximizing_metrics):
            return True
        elif any(metric in func_name for metric in minimizing_metrics):
            return False
        else:
            # Default: assume maximizing (most sklearn metrics are designed this way)
            return True

    def _is_better_score(self, new_score: float, current_best: float, 
                        scoring_function: Callable) -> bool:
        """Determine if the new score is better than the current best."""
        if self._is_maximizing_metric(scoring_function):
            return new_score > current_best
        else:
            return new_score < current_best

    def get_results_dataframe(self) -> pd.DataFrame:
        """
        Get search results as a pandas DataFrame.
        
        Returns:
            DataFrame with parameter combinations and scores
        """
        if not self.results_history:
            return pd.DataFrame()
        
        # Flatten parameter dictionaries
        results_flat = []
        for result in self.results_history:
            flat_result = result['params'].copy()
            flat_result['score'] = result['score']
            if 'error' in result:
                flat_result['error'] = result['error']
            results_flat.append(flat_result)
        
        return pd.DataFrame(results_flat)

    def get_best_model(self, model_class: Any, train_data: Tuple) -> Any:
        """
        Get the best model trained with optimal parameters.
        
        Args:
            model_class: Model class to instantiate
            train_data: Training data (X_train, y_train)
            
        Returns:
            Trained model with best parameters
        """
        if not self.search_completed or self.best_params is None:
            raise ValueError("Search not completed or no best parameters found")
        
        X_train, y_train = train_data
        best_model = model_class(**self.best_params)
        best_model.fit(X_train, y_train)
        
        return best_model

    def save_results(self, file_path: str, format: str = 'csv') -> None:
        """
        Save search results to file.
        
        Args:
            file_path: Path to save results
            format: File format ('csv', 'json', 'pickle')
        """
        results_df = self.get_results_dataframe()
        
        if format == 'csv':
            results_df.to_csv(file_path, index=False)
        elif format == 'json':
            results_df.to_json(file_path, orient='records', indent=2)
        elif format == 'pickle':
            import pickle
            with open(file_path, 'wb') as f:
                pickle.dump({
                    'results_history': self.results_history,
                    'best_params': self.best_params,
                    'best_score': self.best_score
                }, f)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        self.logger.info(f"Results saved to {file_path}")

    def plot_search_progress(self, save_path: str = None) -> None:
        """
        Plot the search progress over iterations.
        
        Args:
            save_path: Path to save the plot (optional)
        """
        try:
            import matplotlib.pyplot as plt
            
            if not self.results_history:
                print("No results to plot")
                return
            
            scores = [result['score'] for result in self.results_history]
            iterations = range(1, len(scores) + 1)
            
            plt.figure(figsize=(10, 6))
            plt.plot(iterations, scores, 'b-', alpha=0.7, label='Score')
            
            # Highlight best score
            best_idx = scores.index(self.best_score)
            plt.scatter([best_idx + 1], [self.best_score], color='red', s=100, 
                       label=f'Best Score: {self.best_score:.4f}', zorder=5)
            
            plt.xlabel('Iteration')
            plt.ylabel('Score')
            plt.title('Hyperparameter Search Progress')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"Plot saved to {save_path}")
            
            plt.show()
            
        except ImportError:
            print("matplotlib not available. Cannot create plot.")
        except Exception as e:
            print(f"Error creating plot: {e}")

    def get_search_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the hyperparameter search.
        
        Returns:
            Dictionary with search summary information
        """
        if not self.results_history:
            return {"status": "No search performed"}
        
        scores = [result['score'] for result in self.results_history if 'error' not in result]
        
        summary = {
            "search_completed": self.search_completed,
            "total_evaluations": len(self.results_history),
            "successful_evaluations": len(scores),
            "failed_evaluations": len(self.results_history) - len(scores),
            "best_score": self.best_score,
            "best_params": self.best_params,
            "score_statistics": {
                "mean": np.mean(scores) if scores else None,
                "std": np.std(scores) if scores else None,
                "min": np.min(scores) if scores else None,
                "max": np.max(scores) if scores else None
            }
        }
        
        return summary