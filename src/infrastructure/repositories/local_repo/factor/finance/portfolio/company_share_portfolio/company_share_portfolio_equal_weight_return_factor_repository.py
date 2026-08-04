from typing import Optional
from sqlalchemy.orm import Session

from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_equal_weight_return_factor import CompanySharePortfolioEqualWeightReturnFactor
from src.domain.entities.factor.factor_dependency import FactorDependency
from src.domain.ports.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_equal_weight_return_factor_port import CompanySharePortfolioEqualWeightReturnFactorPort
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.infrastructure.repositories.mappers.factor.company_share_portfolio_equal_weight_return_factor_mapper import CompanySharePortfolioEqualWeightReturnFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper


class CompanySharePortfolioEqualWeightReturnFactorRepository(BaseFactorRepository, CompanySharePortfolioEqualWeightReturnFactorPort):

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = CompanySharePortfolioEqualWeightReturnFactorMapper()
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
                group=kwargs.get('group') or 'return',
                factor_type=kwargs.get('factor_type') or 'company_share_portfolio_equal_weight_return_factor',
            )
            if existing:
                return self._to_entity(existing)

            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group') or 'return',
                subgroup=kwargs.get('subgroup') or 'daily',
                frequency=kwargs.get('frequency') or '1d',
                data_type=kwargs.get('data_type') or 'numeric',
                source=kwargs.get('source') or 'calculated',
                definition=kwargs.get('definition') or f'{self.mapper.discriminator} equal-weight return factor: {primary_key}',
            )

            orm_factor = self._to_model(domain_factor)
            self.session.add(orm_factor)

            if kwargs.get('dependencies'):
                for dep_name, dep_config in kwargs['dependencies'].items():
                    entity_class = dep_config.get('class')
                    repo = self.factory.get_local_repository(entity_class)
                    dep_entity = repo._create_or_get(
                        entity_class,
                        primary_key=dep_config.get('name'),
                        group=dep_config.get('group'),
                        subgroup=dep_config.get('subgroup'),
                        frequency=dep_config.get('frequency') or '1d',
                        data_type=dep_config.get('data_type'),
                        source=dep_config.get('source'),
                        definition=dep_config.get('definition'),
                        dependencies=dep_config.get('dependencies'),
                    )
                    dep_repo = self.factory.get_local_repository(FactorDependency)
                    lag = (dep_config.get('parameters') or {}).get('lag')
                    dep_repo._create_or_get(
                        independent_factor=dep_entity,
                        dependent_factor=self._to_entity(orm_factor),
                        lag=lag,
                        dependency_name=dep_name,
                    )

            self.session.commit()
            return self._to_entity(orm_factor)

        except Exception as e:
            print(f"Error in _create_or_get CompanySharePortfolioEqualWeightReturnFactor {primary_key}: {e}")
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
            print(f"Error retrieving CompanySharePortfolioEqualWeightReturnFactor by all: {e}")
            return None

    def get_by_id(self, id: int):
        return self._to_entity(self.session.query(self.model_class).filter(self.model_class.id == id).one_or_none())

    def get_by_name(self, name: str):
        orm = self.session.query(self.model_class).filter(self.model_class.name == name).first()
        return self._to_entity(orm) if orm else None

    def get_by_subgroup(self, subgroup: str):
        return [self._to_entity(o) for o in self.session.query(self.model_class).filter(self.model_class.subgroup == subgroup).all()]

    def get_all(self):
        return [self._to_entity(o) for o in self.session.query(self.model_class).all()]

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
