from typing import Optional
from sqlalchemy.orm import Session

from src.domain.entities.factor.finance.holding.company_share_option_portfolio_portfolio.company_share_option_portfolio_portfolio_holding_value_factor import CompanyShareOptionPortfolioPortfolioHoldingValueFactor
from src.domain.entities.factor.factor_dependency import FactorDependency
from src.domain.ports.factor.finance.holding.company_share_option_portfolio_portfolio.company_share_option_portfolio_portfolio_holding_value_factor_port import CompanyShareOptionPortfolioPortfolioHoldingValueFactorPort
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.infrastructure.repositories.mappers.factor.company_share_option_portfolio_portfolio_holding_value_factor_mapper import CompanyShareOptionPortfolioPortfolioHoldingValueFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper


class CompanyShareOptionPortfolioPortfolioHoldingValueFactorRepository(BaseFactorRepository, CompanyShareOptionPortfolioPortfolioHoldingValueFactorPort):

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = CompanyShareOptionPortfolioPortfolioHoldingValueFactorMapper()
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
                group=kwargs.get('group', 'holding'),
                factor_type=kwargs.get('factor_type', 'company_share_option_portfolio_portfolio_holding_value_factor')
            )
            if existing:
                return self._to_entity(existing)

            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group') or 'holding',
                subgroup=kwargs.get('subgroup') or 'value',
                frequency=kwargs.get('frequency') or '5m',
                data_type=kwargs.get('data_type') or 'numeric',
                source=kwargs.get('source') or 'calculated',
                definition=kwargs.get('definition') or f'{self.mapper.discriminator} factor: {primary_key}',
            )

            orm_factor = self._to_model(domain_factor)
            self.session.add(orm_factor)

            if kwargs.get('dependencies'):
                dependencies = kwargs.get('dependencies')
                for dependency in dependencies.items():
                    entity_class = dependency[1].get('class')
                    repo = self.factory.get_local_repository(entity_class)
                    dependency_config = dependency[1]
                    dependency_entity = repo._create_or_get(
                        entity_class,
                        primary_key=dependency_config.get("name"),
                        group=dependency_config.get("group"),
                        subgroup=dependency_config.get("subgroup"),
                        frequency=dependency_config.get("frequency", "5m"),
                        data_type=dependency_config.get("data_type"),
                        factor_type=dependency_config.get("factor_type"),
                        source=dependency_config.get("source"),
                        definition=dependency_config.get("definition"),
                        dependencies=dependency_config.get("dependencies"),
                    )
                    repo_factor_dependency = self.factory.get_local_repository(FactorDependency)
                    lag = dependency_config.get("parameters", {}).get("lag", None) if dependency_config.get("parameters") else None
                    independent_factor_related_entity_key = dependency_config.get("parameters", {}).get("independent_factor_related_entity_key", None) if dependency_config.get("parameters") else None
                    repo_factor_dependency._create_or_get(
                        independent_factor=dependency_entity,
                        dependent_factor=self._to_entity(orm_factor),
                        lag=lag,
                        independent_factor_related_entity_key=independent_factor_related_entity_key,
                        dependency_name=dependency[0]
                    )

            self.session.commit()
            if orm_factor:
                return self._to_entity(orm_factor)

        except Exception as e:
            print(f"Error in get_or_create company share option portfolio portfolio holding value factor {primary_key}: {e}")
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
            print(f"Error retrieving company share option portfolio portfolio holding value factor by all attributes: {e}")
            return None

    def get_by_id(self, id: int):
        return self._to_entity(self.session.query(self.model_class).filter(self.model_class.id == id).one_or_none())

    def get_by_name(self, name: str):
        orm = self.session.query(self.model_class).filter(self.model_class.name == name).first()
        return self._to_entity(orm) if orm else None

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
