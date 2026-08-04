from typing import Optional
from sqlalchemy.orm import Session

from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_factor import CompanySharePortfolioFactor
from src.domain.ports.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_factor_port import CompanySharePortfolioFactorPort
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.infrastructure.repositories.mappers.factor.company_share_portfolio_factor_mapper import CompanySharePortfolioFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper


class CompanySharePortfolioFactorRepository(BaseFactorRepository, CompanySharePortfolioFactorPort):

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = CompanySharePortfolioFactorMapper()
        self.mapper_value = FactorValueMapper()

    @property
    def entity_class(self):
        return self.get_factor_entity()

    @property
    def model_class(self):
        return self.mapper.model_class

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs):
        try:
            existing = self.get_by_all(
                name=primary_key,
                group=kwargs.get('group') or 'price',
                factor_type=kwargs.get('factor_type') or 'company_share_portfolio_factor',
            )
            if existing:
                return self._to_entity(existing)

            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group') or 'price',
                subgroup=kwargs.get('subgroup') or 'daily',
                frequency=kwargs.get('frequency') or '1d',
                data_type=kwargs.get('data_type') or 'numeric',
                source=kwargs.get('source') or 'ibkr',
                definition=kwargs.get('definition') or f'CompanySharePortfolioFactor: {primary_key}',
            )

            orm_factor = self._to_model(domain_factor)
            self.session.add(orm_factor)
            self.session.commit()
            return self._to_entity(orm_factor)

        except Exception as e:
            print(f"Error in _create_or_get CompanySharePortfolioFactor {primary_key}: {e}")
            return None

    def get_by_all(self, name, group, factor_type=None, subgroup=None, frequency=None, data_type=None, source=None):
        try:
            Model = self.get_factor_model()
            q = self.session.query(Model).filter(Model.name == name, Model.group == group)
            if factor_type is not None:
                q = q.filter(Model.factor_type == factor_type)
            if subgroup is not None:
                q = q.filter(Model.subgroup == subgroup)
            if frequency is not None:
                q = q.filter(Model.frequency == frequency)
            if data_type is not None:
                q = q.filter(Model.data_type == data_type)
            if source is not None:
                q = q.filter(Model.source == source)
            return q.first()
        except Exception as e:
            print(f"Error retrieving CompanySharePortfolioFactor by all: {e}")
            return None

    def get_by_id(self, id: int):
        return self._to_entity(self.session.query(self.model_class).filter(self.model_class.id == id).one_or_none())

    def get_by_name(self, name: str):
        orm = self.session.query(self.model_class).filter(self.model_class.name == name).first()
        return self._to_entity(orm) if orm else None

    def get_by_group(self, group: str):
        return [self._to_entity(o) for o in
                self.session.query(self.model_class).filter(self.model_class.group == group).all()]

    def get_all(self):
        return [self._to_entity(o) for o in self.session.query(self.model_class).all()]

    def add(self, entity):
        orm = self._to_model(entity)
        self.session.add(orm)
        self.session.commit()
        return self._to_entity(orm)

    def update(self, entity):
        orm = self.session.query(self.model_class).filter(self.model_class.id == entity.factor_id).one_or_none()
        if not orm:
            return None
        orm.name = entity.name
        orm.group = entity.group
        orm.subgroup = entity.subgroup
        orm.frequency = entity.frequency
        orm.data_type = entity.data_type
        orm.source = entity.source
        orm.definition = entity.definition
        self.session.commit()
        return self._to_entity(orm)

    def delete(self, id: int) -> bool:
        orm = self.session.query(self.model_class).filter(self.model_class.id == id).one_or_none()
        if not orm:
            return False
        self.session.delete(orm)
        self.session.commit()
        return True

    def get_factor_model(self):
        return self.mapper.get_factor_model()

    def get_factor_entity(self):
        return self.mapper.get_factor_entity()

    def get_factor_value_model(self):
        return self.mapper_value.get_factor_value_model()

    def get_factor_value_entity(self):
        return self.mapper_value.get_factor_value_entity()

    def _to_entity(self, infra_obj):
        return self.mapper.to_domain(infra_obj)

    def _to_model(self, entity):
        return self.mapper.to_orm(entity)
