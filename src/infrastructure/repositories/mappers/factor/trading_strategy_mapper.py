"""
src/infrastructure/repositories/mappers/factor/trading_strategy_mapper.py

Mapper for the TradingStrategy factor domain entity <-> ORM model (factors table, factor_type 'trading_strategy').
"""

from typing import Optional

from src.domain.entities.factor.trading_strategy.trading_strategy import TradingStrategy
from src.infrastructure.models.factor.factor import TradingStrategyModel


class TradingStrategyMapper:

    @property
    def discriminator(self) -> str:
        return "trading_strategy"

    @property
    def model_class(self):
        return TradingStrategyModel

    def get_entity(self):
        return TradingStrategy

    def get_factor_model(self):
        return TradingStrategyModel

    def get_factor_entity(self):
        return TradingStrategy

    def to_domain(self, orm_model: Optional[TradingStrategyModel]) -> Optional[TradingStrategy]:
        if not orm_model:
            return None
        return TradingStrategy(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, entity: TradingStrategy) -> TradingStrategyModel:
        return TradingStrategyModel(
            id=entity.id,
            name=entity.name,
            group=entity.group,
            subgroup=entity.subgroup,
            frequency=entity.frequency,
            data_type=entity.data_type,
            source=entity.source,
            definition=entity.definition,
        )
