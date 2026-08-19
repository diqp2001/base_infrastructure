"""
SPX call spread model training pipeline.

Extends BaseModelTrainer (factor creation + data preparation) with the
project-specific steps: normalisation, tensor creation, model training,
and performance evaluation.
"""

import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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
        factor_data = self._prepare_factor_data(date, bar_size_setting, duration_str)

        print("\nStep 2: Normalizing and enhancing factors...")
        # normalized_factor_data = self._normalize_and_enhance_factors(factor_data)

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
    # Normalisation
    # ------------------------------------------------------------------

    def _normalize_and_enhance_factors(self, factor_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        enhanced = self.factor_normalizer.apply_comprehensive_normalization(factor_data)
        for ticker, df in enhanced.items():
            orig = len(factor_data[ticker].columns) if ticker in factor_data else 0
            print(f"  {ticker}: {orig} → {len(df.columns)} factors")
        return enhanced

    # ------------------------------------------------------------------
    # Tensor creation
    # ------------------------------------------------------------------

    def _create_training_tensors(self, factor_data: Dict[str, pd.DataFrame], model_type: str) -> Dict[str, Any]:
        tensor_data = {}
        expected_features = (
            self.features_config.get('momentum_features', []) +
            self.features_config.get('technical_features', [])
        )
        feature_cols = self._map_factor_names(factor_data, expected_features)

        if model_type in ['tft', 'both']:
            combined = self._combine_data_for_multivariate(factor_data)
            tensor_data['multivariate'] = self.tensor_splitter.create_multivariate_tensors(
                data=combined, cols=feature_cols, target_col='target_returns',
                timesteps=self.training_config.get('history_size'),
                batch_size=self.training_config.get('batch_size'),
                encoder_length=self.training_config.get('encoder_length'),
            )

        if model_type in ['mlp', 'both']:
            tensor_data['univariate'] = self.tensor_splitter.create_univariate_tensors(
                data=factor_data, cols=feature_cols, target_col='target_returns',
                timesteps=21, encoder_length=None,
            )

        return tensor_data

    def _map_factor_names(self, factor_data: Dict[str, pd.DataFrame], expected_features: List[str]) -> List[str]:
        if not factor_data:
            return expected_features

        available = set(factor_data[next(iter(factor_data))].columns)
        mapped = []

        for name in expected_features:
            if name in available:
                mapped.append(name)
                continue

            if name.startswith('macd_'):
                parts = name.split('_')
                if len(parts) >= 3:
                    fast, slow = parts[1], parts[2]
                    candidates = [
                        'macd', 'MACD', f'macd_{fast}_{slow}', f'MACD_{fast}_{slow}',
                        'macd_line', f'macd_line_{fast}_{slow}',
                    ]
                    mapped.append(next((c for c in candidates if c in available), name))
                    continue

            if name.startswith('norm_') and name.endswith('_return'):
                momentum_map = {
                    'norm_daily_return': ['deep_momentum_1d', 'momentum_1d'],
                    'norm_monthly_return': ['deep_momentum_5d', 'momentum_5d'],
                    'norm_quarterly_return': ['deep_momentum_21d', 'momentum_21d'],
                    'norm_biannual_return': ['deep_momentum_63d', 'momentum_63d'],
                    'norm_annual_return': ['deep_momentum_126d', 'momentum_126d'],
                }
                candidates = momentum_map.get(name, [])
                mapped.append(next((c for c in candidates if c in available), name))
                continue

            mapped.append(name)

        return mapped

    def _combine_data_for_multivariate(self, factor_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        preserve = (
            self.features_config.get('momentum_features', []) +
            self.features_config.get('technical_features', []) +
            self.features_config.get('volatility_features', []) +
            ['target_returns', 'target_returns_nonscaled', 'daily_vol', 'monthly_vol', 'asset']
        )
        combined = []
        for ticker, data in factor_data.items():
            d = data.copy()
            d['asset'] = ticker
            rename = {c: f"{ticker}_{c}" for c in data.columns if c not in preserve and c != 'Date'}
            combined.append(d.rename(columns=rename))
        return pd.concat(combined, axis=0, ignore_index=False).sort_index()

    # ------------------------------------------------------------------
    # Model training and evaluation
    # ------------------------------------------------------------------

    def _train_models(self, tensor_data: Dict[str, Any], model_type: str, seeds: List[int]) -> Dict[str, Any]:
        training_results = {}
        start, end = self.training_config.get('train_date_range', (None, None))
        date_range = [pd.to_datetime(d) for d in pd.date_range(start, end, freq='365D')]

        if model_type in ['tft', 'both'] and 'multivariate' in tensor_data:
            training_results['tft'] = self.model.train_rolling_window_models(
                data_splitter=tensor_data['multivariate'], date_range=date_range,
                model_type='tft', seeds=seeds,
            )
        if model_type in ['mlp', 'both'] and 'univariate' in tensor_data:
            training_results['mlp'] = self.model.train_rolling_window_models(
                data_splitter=tensor_data['univariate'], date_range=date_range,
                model_type='mlp', seeds=seeds,
            )
        return training_results

    def _evaluate_model_performance(self, training_results: Dict[str, Any]) -> Dict[str, Any]:
        summary = {
            'models_trained': 0, 'average_validation_correlation': 0.0,
            'average_test_correlation': 0.0, 'best_model': None, 'performance_details': {},
        }
        all_val, all_test, best_score = [], [], -1.0

        for model_type, results in training_results.items():
            perf = {'validation_correlations': [], 'test_correlations': [], 'model_count': 0}
            for seed, seed_results in results.items():
                for date, date_results in seed_results.items():
                    if model_type in date_results and 'performance' in date_results[model_type]:
                        p = date_results[model_type]['performance']
                        if 'validation_correlation' in p:
                            perf['validation_correlations'].append(p['validation_correlation'])
                            all_val.append(p['validation_correlation'])
                        if 'test_correlation' in p:
                            tc = p['test_correlation']
                            perf['test_correlations'].append(tc)
                            all_test.append(tc)
                            if tc > best_score:
                                best_score = tc
                                summary['best_model'] = {'type': model_type, 'seed': seed,
                                                          'date': date, 'test_correlation': tc}
                    perf['model_count'] += 1
                    summary['models_trained'] += 1

            if perf['validation_correlations']:
                perf['avg_validation_correlation'] = np.mean(perf['validation_correlations'])
            if perf['test_correlations']:
                perf['avg_test_correlation'] = np.mean(perf['test_correlations'])
            summary['performance_details'][model_type] = perf

        if all_val:
            summary['average_validation_correlation'] = np.mean(all_val)
        if all_test:
            summary['average_test_correlation'] = np.mean(all_test)
            summary['overall_score'] = np.mean(all_test)
        return summary

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _summarize_factor_data(self, factor_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        return {
            'tickers': list(factor_data.keys()),
            'total_records': sum(len(df) for df in factor_data.values()),
            'feature_columns': list(next(iter(factor_data.values())).columns) if factor_data else [],
            'date_range': (
                min(df.index.min() for df in factor_data.values()) if factor_data else None,
                max(df.index.max() for df in factor_data.values()) if factor_data else None,
            ),
        }

    def _summarize_tensor_data(self, tensor_data: Dict[str, Any]) -> Dict[str, Any]:
        return {t: {'type': t, 'splitter_class': s.__class__.__name__, 'ready_for_training': True}
                for t, s in tensor_data.items()}

    def save_training_results(self, results: Dict[str, Any], filepath: Optional[str] = None) -> str:
        if filepath is None:
            filepath = f"results/training_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(results, f)
        return filepath

    def get_trained_model(self) -> Any:
        return self.model
