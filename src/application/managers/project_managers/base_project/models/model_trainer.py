"""
Base project model training pipeline.

Extends BaseModelTrainer (factor creation + data preparation) with the
project-specific steps. Override these methods in a concrete project.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from src.application.services.misbuffet.engine.base_model_trainer import BaseModelTrainer
from ..config import get_config, get_trading_config


class ModelTrainer(BaseModelTrainer):

    def __init__(self, database_service):
        super().__init__(database_service, get_config(), get_trading_config())
        self.model = None
        self.tensor_splitter = None

    # ------------------------------------------------------------------
    # Pipeline orchestration
    # ------------------------------------------------------------------

    def train_complete_pipeline(
        self,
        tickers: Optional[List[str]] = None,
        model_type: str = 'both',
        seeds: Optional[List[int]] = None,
        data=None,
    ) -> Dict[str, Any]:
        if seeds is None:
            seeds = [42, 123]

        date = list(data.items())[0][1].time
        bar_size_setting = data.bar_size_setting
        duration_str = data.duration_str

        print("\nStep 1: Preparing factor-enhanced data...")
        _ = self._prepare_factor_data(date, bar_size_setting, duration_str)

        print("\nStep 2: Normalizing and enhancing factors...")
        # normalized_factor_data = self._normalize_and_enhance_factors(_)

        print("\nStep 3: Creating training tensors...")
        # tensor_data = self._create_training_tensors(normalized_factor_data, model_type)

        print("\nStep 4: Training models...")
        # training_results = self._train_models(tensor_data, model_type, seeds)

        print("\nStep 5: Evaluating model performance...")
        # performance_summary = self._evaluate_model_performance(training_results)

        return {
            'tickers': tickers,
            'model_type': model_type,
            'training_completed': datetime.now().isoformat(),
            'factors_stored_in_database': True,
        }

    # ------------------------------------------------------------------
    # Project-specific steps — override in concrete projects
    # ------------------------------------------------------------------

    def _normalize_and_enhance_factors(self, factor_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        return self.factor_normalizer.apply_comprehensive_normalization(factor_data)

    def _create_training_tensors(self, factor_data: Dict[str, pd.DataFrame], model_type: str) -> Dict[str, Any]:
        del factor_data, model_type
        return {}

    def _map_factor_names(self, factor_data: Dict[str, pd.DataFrame], expected_features: List[str]) -> List[str]:
        del factor_data
        return expected_features

    def _combine_data_for_multivariate(self, factor_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        return pd.concat(list(factor_data.values()), axis=0).sort_index()

    def _train_models(self, tensor_data: Dict[str, Any], model_type: str, seeds: List[int]) -> Dict[str, Any]:
        del tensor_data, model_type, seeds
        return {}

    def _evaluate_model_performance(self, training_results: Dict[str, Any]) -> Dict[str, Any]:
        del training_results
        return {}

    def get_trained_model(self) -> Any:
        return self.model
