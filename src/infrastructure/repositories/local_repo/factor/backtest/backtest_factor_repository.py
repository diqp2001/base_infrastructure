from typing import Optional
from sqlalchemy.orm import Session

from src.infrastructure.repositories.mappers.factor.backtest.backtest_factor_mapper import BacktestFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.domain.ports.factor.backtest.backtest_factor_port import BacktestFactorPort


class BacktestFactorRepository(BaseFactorRepository, BacktestFactorPort):

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = BacktestFactorMapper()
        self.mapper_value = FactorValueMapper()

    @property
    def entity_class(self):
        return self.mapper.get_factor_entity()

    @property
    def model_class(self):
        return self.mapper.get_factor_model()

    def get_factor_model(self):
        return self.mapper.get_factor_model()

    def get_factor_entity(self):
        return self.mapper.get_factor_entity()

    def get_factor_value_model(self):
        return self.mapper_value.get_factor_value_model()

    def get_factor_value_entity(self):
        return self.mapper_value.get_factor_value_entity()

    def _to_entity(self, infra_obj):
        return BacktestFactorMapper.to_domain(infra_obj)

    def _to_model(self, entity):
        return BacktestFactorMapper.to_orm(entity)

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs):
        try:
            existing = self.get_by_all(
                name=primary_key,
                group=kwargs.get('group', 'fundamental'),
                factor_type=kwargs.get('factor_type', 'backtest_factor'),
            )
            if existing:
                return self._to_entity(existing)

            FactorEntity = self.get_factor_entity()
            domain_factor = FactorEntity(
                name=primary_key,
                group=kwargs.get('group', 'fundamental'),
                subgroup=kwargs.get('subgroup', 'signal'),
                frequency=kwargs.get('frequency', '1d'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'calculated'),
                definition=kwargs.get('definition', f'Backtest factor: {primary_key}'),
            )
            orm_factor = self._to_model(domain_factor)
            self.session.add(orm_factor)
            self.session.commit()
            return self._to_entity(orm_factor)
        except Exception as e:
            print(f"Error in _create_or_get for BacktestFactor '{primary_key}': {e}")
            return None

    def get_by_id(self, id: int):
        orm = self.session.get(self.model_class, id)
        return self._to_entity(orm) if orm else None

    def get_by_name(self, name: str):
        orm = (
            self.session.query(self.model_class)
            .filter(self.model_class.name == name)
            .first()
        )
        return self._to_entity(orm) if orm else None

    def get_all(self):
        return [self._to_entity(o) for o in self.session.query(self.model_class).all()]

    def add(self, entity):
        if entity.id is None:
            entity.id = self._get_next_available_id()
        orm = self._to_model(entity)
        self.session.add(orm)
        self.session.commit()
        self.session.refresh(orm)
        return self._to_entity(orm)

    def update(self, entity):
        orm = self.session.get(self.model_class, entity.id)
        if orm is None:
            return None
        for field in ('name', 'group', 'subgroup', 'frequency', 'data_type', 'source', 'definition'):
            if hasattr(entity, field):
                setattr(orm, field, getattr(entity, field))
        self.session.commit()
        self.session.refresh(orm)
        return self._to_entity(orm)

    def get_by_all(self, name: str, group: str, factor_type=None, subgroup=None,
                   frequency=None, data_type=None, source=None):
        try:
            FactorModel = self.get_factor_model()
            query = self.session.query(FactorModel).filter(
                FactorModel.name == name,
                FactorModel.group == group,
            )
            if factor_type is not None:
                query = query.filter(FactorModel.factor_type == factor_type)
            if subgroup is not None:
                query = query.filter(FactorModel.subgroup == subgroup)
            if frequency is not None:
                query = query.filter(FactorModel.frequency == frequency)
            if data_type is not None:
                query = query.filter(FactorModel.data_type == data_type)
            if source is not None:
                query = query.filter(FactorModel.source == source)
            return query.first()
        except Exception as e:
            print(f"Error in get_by_all for BacktestFactor: {e}")
            return None
