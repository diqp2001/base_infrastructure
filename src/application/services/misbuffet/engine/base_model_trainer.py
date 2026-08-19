"""
BaseModelTrainer — generic factor creation and preparation pipeline.

Covers everything up to and including factor data retrieval from the DB.
Project-specific steps (normalisation strategy, tensor format, model
training, evaluation) belong in the project's ModelTrainer subclass.
"""

import logging
from abc import ABC
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from src.application.services.misbuffet.data.base_data_loader import BaseDataLoader
from src.application.services.misbuffet.data.factor_manager import FactorManager
from src.application.services.misbuffet.data.factor_normalizer import FactorNormalizer
from src.domain.entities.factor.factor import Factor


class BaseModelTrainer(ABC):
    """
    Generic factor-layer pipeline shared across all projects.

    Provides:
      - Service wiring (DataLoader, FactorManager, FactorNormalizer)
      - Factor creation from config (_ensure_factors_exist, create_factors)
      - Factor data preparation (_prepare_factor_data)
      - Price-factor dependency creation helpers

    Projects subclass this, call super().__init__() with their config,
    then implement their own train_complete_pipeline and model-specific steps.
    """

    def __init__(self, database_service, config: Dict, training_config: Optional[Dict] = None):
        self.database_service = database_service
        self.config = config
        self.training_config = training_config or {}
        self.features_config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        self.data_loader = BaseDataLoader(database_service)
        self.factor_manager = FactorManager(database_service)
        self.factor_normalizer = FactorNormalizer(database_service)

    # ------------------------------------------------------------------
    # Factor creation
    # ------------------------------------------------------------------

    def _ensure_factors_exist(self) -> Dict[str, Any]:
        results = {
            'factors_created': 0,
            'factors_skipped': 0,
            'factor_details': [],
            'return_factor_details': [],
            'errors': [],
            'factor_batches': [],
        }
        try:
            factors_config = self.config.get('factors', [])
            if factors_config:
                factor_results = self.create_factors(factors_config)
                results['config_factors_created'] = factor_results['factors_created']
                results['config_factor_details'] = factor_results['factor_details']
            return results
        except Exception as e:
            results['errors'].append(str(e))
            return results

    def create_factors(self, factors_config: List[Dict]) -> Dict[str, Any]:
        results = {'factors_created': 0, 'factor_details': [], 'errors': []}
        try:
            for factor_config in factors_config:
                if not isinstance(factor_config, dict):
                    continue
                factor_name = factor_config.get('name')
                if not factor_name:
                    continue
                try:
                    creation_config = {
                        'entity_class': factor_config.get('class', 'unknown'),
                        'name': factor_name,
                        'entity_symbol': factor_name,
                        'group': factor_config.get('group', 'unknown'),
                        'subgroup': factor_config.get('subgroup', 'default'),
                        'data_type': factor_config.get('data_type', 'numeric'),
                        'source': factor_config.get('source', 'calculated'),
                        'frequency': factor_config.get('frequency'),
                        'definition': factor_config.get('definition', f'Factor {factor_name} from config'),
                        'factor_index': results['factors_created'],
                        'factor_future_start': datetime.now(),
                        'dependencies': factor_config.get('dependencies'),
                    }
                    factor_entity = None
                    if hasattr(self.data_loader, 'market_data_history_service'):
                        factor_entity = self.data_loader.market_data_history_service._create_or_get(creation_config)
                    if factor_entity:
                        results['factors_created'] += 1
                        results['factor_details'].append({
                            'factor_entity': factor_entity,
                            'name': factor_name,
                            'group': factor_config.get('group', 'unknown'),
                            'subgroup': factor_config.get('subgroup', 'default'),
                            'status': 'created',
                        })
                    else:
                        results['errors'].append(f"Failed to create factor {factor_name}")
                except Exception as e:
                    results['errors'].append(f"Error creating factor {factor_name}: {e}")
            return results
        except Exception as e:
            results['errors'].append(str(e))
            return results

    def _create_factor_from_config(
        self, name: str, group: str, subgroup: str, data_type: str,
        tickers: List[str], overwrite: bool = False,
    ):
        try:
            if hasattr(self.data_loader, 'factor_data_service'):
                return self.data_loader.factor_data_service.create_or_get_factor(
                    name=name, group=group, subgroup=subgroup, data_type=data_type,
                    source='calculated',
                    definition=f'Factor {name} from {group}/{subgroup} configuration',
                )
            return Factor(
                name=name, group=group, subgroup=subgroup, data_type=data_type,
                source='calculated',
                definition=f'Factor {name} from {group}/{subgroup} configuration',
            )
        except Exception as e:
            self.logger.error(f"Error creating factor {name}: {e}")
            return None

    def _create_price_dependencies_for_return_factor(
        self, return_factor: Any, symbol: str, asset_class: type, price_factor_names: List[str],
    ) -> int:
        from src.domain.entities.factor.factor_dependency import FactorDependency

        dependencies_created = 0
        try:
            for price_factor_name in price_factor_names:
                try:
                    config = {
                        'entity_class': type(return_factor),
                        'entity_symbol': f"{symbol}_{price_factor_name}",
                        'name': f"{symbol}_{price_factor_name}",
                        'group': 'price', 'subgroup': 'ohlc', 'data_type': 'numeric',
                        'source': 'market_data',
                        'definition': f'{price_factor_name.title()} price factor for {symbol}',
                        'underlying_symbol': symbol,
                    }
                    price_factor = self.data_loader.market_data_history_service._create_or_get(config)
                    if price_factor and hasattr(return_factor, 'id') and hasattr(price_factor, 'id'):
                        FactorDependency(
                            dependent_factor_id=return_factor.id,
                            independent_factor_id=price_factor.id,
                            dependency_type='calculation',
                            description=f'{return_factor.name} depends on {price_factor.name}',
                        )
                        dependencies_created += 1
                except Exception as e:
                    self.logger.error(f"Error creating dependency for {price_factor_name}: {e}")
            return dependencies_created
        except Exception as e:
            self.logger.error(f"Error in _create_price_dependencies_for_return_factor: {e}")
            return dependencies_created

    # ------------------------------------------------------------------
    # Data preparation
    # ------------------------------------------------------------------

    def _load_ticker_price_data(self, ticker: str) -> Optional[pd.DataFrame]:
        try:
            company = self.factor_manager.company_share_repository.get_by_ticker(ticker)
            if not company:
                return None
            company = company[0] if isinstance(company, list) else company
            column_mapping = {
                'Open': 'open_price', 'High': 'high_price', 'Low': 'low_price',
                'Close': 'close_price', 'Adj Close': 'adj_close_price', 'Volume': 'volume',
            }
            price_data = {}
            for factor_name in column_mapping:
                fe = self.factor_manager.share_factor_repository.get_by_name(factor_name)
                if fe:
                    df = self.factor_manager.share_factor_repository.get_factor_values_df(
                        factor_id=int(fe.id), entity_id=company.id,
                    )
                    if df is not None and not df.empty:
                        df['date'] = pd.to_datetime(df['date'])
                        df.set_index('date', inplace=True)
                        price_data[column_mapping[factor_name]] = df['value'].astype(float)
            if not price_data:
                return None
            result = pd.DataFrame(price_data)
            result.index.name = 'Date'
            return result
        except Exception as e:
            self.logger.error(f"Error loading price data for {ticker}: {e}")
            return None

    def _prepare_factor_data(self, date, bar_size_setting, duration_str) -> Dict[str, pd.DataFrame]:
        results = self._ensure_factors_exist()
        if not date:
            date = datetime.now()
        self.data_loader.market_data_history_service.set_frontier(date)
        factor_groups = results.get('config_factor_details', [])
        entities = []

        for entity_class, entity_list in self.config.get('universe', {}).items():
            if isinstance(entity_list, dict) :
                container_repo = self.data_loader.market_data_history_service.market_data_service.entity_service.repository_factory.get_local_repository(entity_class)
                container = container_repo._create_or_get( **entity_list.get('args', {}))
                if container:
                    entities.append(container)

                for component_class, component_tickers in entity_list['components'].items():
                    
                    for component_ticker in component_tickers:
                        component = self.data_loader.market_data_history_service.market_data_service.create_entity_from_ticker_item(component_ticker,component_class)
                        if component:
                            entities.append(component)
            else:
                for ticker_item in entity_list:
                    entity = self.data_loader.market_data_history_service.market_data_service\
                        .create_entity_from_ticker_item(ticker_item, entity_class)

                    if entity:
                        entities.append(entity)

        return self.data_loader.market_data_history_service._create_or_get_factor_value_batch(
            factor_groups=factor_groups, entities=entities,
            date=date, duration_str=duration_str, bar_size_setting=bar_size_setting,
        )
