"""
Repository class for Company Share Option Gamma factor entities.
"""

from typing import Optional
from sqlalchemy.orm import Session
from src.domain.entities.factor.factor_dependency import FactorDependency
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_gamma_factor_mapper import CompanyShareOptionGammaFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_gamma_factor import CompanyShareOptionGammaFactor


class CompanyShareOptionGammaFactorRepository(BaseFactorRepository):
    """Repository for Company Share Option Gamma factor entities with CRUD operations."""

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = CompanyShareOptionGammaFactorMapper()

    @property
    def entity_class(self):
        return self.get_factor_entity()

    @property
    def model_class(self):
        return self.mapper.model_class

    def get_factor_model(self):
        return self.mapper.get_factor_model()

    def get_factor_entity(self):
        return self.mapper.get_factor_entity()

    def get_by_id(self, id: int):
        return (
            self.session
            .query(self.model_class)
            .filter(self.model_class.id == id)
            .one_or_none()
        )

    def get_factor_value_model(self):
        return FactorValueMapper().get_factor_value_model()

    def get_factor_value_entity(self):
        return FactorValueMapper().get_factor_value_entity()

    def _to_entity(self, infra_obj):
        return self.mapper.to_domain(infra_obj)

    def _to_model(self, entity):
        return self.mapper.to_orm(entity)

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs):
        try:
            existing = self.get_by_all(
                frequency=kwargs.get('frequency'),
                name=primary_key,
                group=kwargs.get('group') or 'greek',
                subgroup=kwargs.get('subgroup') or 'gamma',
                data_type=kwargs.get('data_type') or 'numeric',
                source=kwargs.get('source') or 'calculated',
            )
            if existing:
                return self._to_entity(existing)

            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group') or 'greek',
                subgroup=kwargs.get('subgroup') or 'gamma',
                frequency=kwargs.get('frequency') or '1d',
                data_type=kwargs.get('data_type') or 'numeric',
                source=kwargs.get('source') or 'calculated',
                definition=kwargs.get('definition') or f'{self.mapper.discriminator} factor: {primary_key}',
            )

            orm_factor = self._to_model(domain_factor)
            self.session.add(orm_factor)

            if kwargs.get('dependencies'):
                for dependency in kwargs['dependencies'].items():
                    entity_class = dependency[1].get('class')
                    repo = self.factory.get_local_repository(entity_class)
                    dependency_config = dependency[1]
                    dependency_entity = repo._create_or_get(
                        entity_class,
                        primary_key=dependency_config.get('name'),
                        group=dependency_config.get('group'),
                        subgroup=dependency_config.get('subgroup'),
                        frequency=dependency_config.get('frequency', '1d'),
                        data_type=dependency_config.get('data_type'),
                        source=dependency_config.get('source'),
                        definition=dependency_config.get('definition'),
                    )
                    repo_factor_dependency = self.factory.get_local_repository(FactorDependency)
                    lag = dependency_config.get('parameters', {}).get('lag') if dependency_config.get('parameters') else None
                    repo_factor_dependency._create_or_get(
                        independent_factor=dependency_entity,
                        dependent_factor=self._to_entity(orm_factor),
                        lag=lag,
                        dependency_name=dependency[0],
                    )

            self.session.commit()
            if orm_factor:
                return self._to_entity(orm_factor)

        except Exception as e:
            print(f"Error in _create_or_get for company share option gamma factor {primary_key}: {e}")
            return None

    def get_by_all(
        self,
        name: str,
        group: str,
        factor_type: str = None,
        subgroup: Optional[str] = None,
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
    ):
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
            print(f"Error retrieving company share option gamma factor by all attributes: {e}")
            return None