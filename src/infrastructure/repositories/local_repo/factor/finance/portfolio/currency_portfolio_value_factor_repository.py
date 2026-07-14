from typing import Optional
from sqlalchemy.orm import Session

from src.domain.entities.factor.finance.portfolio.currency_portfolio_value_factor import CurrencyPortfolioValueFactor
from src.domain.entities.factor.factor_dependency import FactorDependency
from src.domain.ports.factor.currency_portfolio_value_factor_port import CurrencyPortfolioValueFactorPort
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.infrastructure.repositories.mappers.factor.currency_portfolio_value_factor_mapper import CurrencyPortfolioValueFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper


class CurrencyPortfolioValueFactorRepository(BaseFactorRepository, CurrencyPortfolioValueFactorPort):
    """Local repository for currency portfolio value factor entities."""

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = CurrencyPortfolioValueFactorMapper()
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
                group=kwargs.get('group', 'value'),
                factor_type=kwargs.get('factor_type', 'currency_portfolio_value_factor'),
            )
            if existing:
                return self._to_entity(existing)

            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group', 'value'),
                subgroup=kwargs.get('subgroup', 'portfolio'),
                frequency=kwargs.get('frequency', '1d'),
                data_type=kwargs.get('data_type', 'numeric'),
            )

            orm_factor = self._to_model(domain_factor)
            self.session.add(orm_factor)

            if kwargs.get('dependencies'):
                for dependency in kwargs['dependencies'].items():
                    entity_class = dependency[1].get('class')
                    repo = self.factory.get_local_repository(entity_class)
                    dep_cfg = dependency[1]
                    dep_entity = repo._create_or_get(
                        entity_class,
                        primary_key=dep_cfg.get('name'),
                        group=dep_cfg.get('group'),
                        subgroup=dep_cfg.get('subgroup'),
                        frequency=dep_cfg.get('frequency', '1d'),
                        data_type=dep_cfg.get('data_type'),
                        factor_type=dep_cfg.get('factor_type'),
                        source=dep_cfg.get('source'),
                        definition=dep_cfg.get('definition'),
                        dependencies=dep_cfg.get('dependencies'),
                    )
                    dep_repo = self.factory.get_local_repository(FactorDependency)
                    lag = dep_cfg.get('parameters', {}).get('lag') if dep_cfg.get('parameters') else None
                    key = dep_cfg.get('parameters', {}).get('independent_factor_related_entity_key') if dep_cfg.get('parameters') else None
                    dep_repo._create_or_get(
                        independent_factor=dep_entity,
                        dependent_factor=self._to_entity(orm_factor),
                        lag=lag,
                        independent_factor_related_entity_key=key,
                        dependency_name=dependency[0],
                    )

            self.session.commit()
            if orm_factor:
                return self._to_entity(orm_factor)

        except Exception as e:
            print(f"Error in get_or_create currency portfolio value factor {primary_key}: {e}")
            return None

    def get_by_all(self, name: str, group: str, factor_type: Optional[str] = None,
                   subgroup: Optional[str] = None, frequency: Optional[str] = None,
                   data_type: Optional[str] = None, source: Optional[str] = None):
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
            print(f"Error retrieving currency portfolio value factor by all attributes: {e}")
            return None

    def get_by_id(self, id: int):
        return self._to_entity(
            self.session.query(self.model_class).filter(self.model_class.id == id).one_or_none()
        )

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
