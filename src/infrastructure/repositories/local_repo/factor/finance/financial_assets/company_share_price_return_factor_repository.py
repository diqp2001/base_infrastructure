"""
Repository class for CompanySharePriceReturnFactor entities - mirrors IndexPriceReturnFactorRepository structure.
"""
import os
import logging
from sqlalchemy.orm import Session
from typing import Optional

from src.domain.entities.factor.factor_dependency import FactorDependency
from infrastructure.repositories.mappers.factor.finance.financial_assets.share.company_share.company_share_price_return_factor_mapper import CompanySharePriceReturnFactorMapper
from src.infrastructure.models.factor.factor import FactorModel
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_price_return_factor import CompanySharePriceReturnFactor
from src.domain.ports.factor.company_share_price_return_factor_port import CompanySharePriceReturnFactorPort
from ...base_factor_repository import BaseFactorRepository

logger = logging.getLogger(__name__)


class CompanySharePriceReturnFactorRepository(BaseFactorRepository, CompanySharePriceReturnFactorPort):
    """Repository for CompanySharePriceReturnFactor entities with CRUD operations."""
    
    def __init__(self, session: Session, factory=None, mapper: CompanySharePriceReturnFactorMapper = None):
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or CompanySharePriceReturnFactorMapper()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Factor."""
        return self.mapper.get_factor_model()
    
    @property
    def entity_class(self):
        """Return the domain entity class for CompanySharePriceReturnFactor."""
        return self.mapper.get_factor_entity()
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs):
        """
        
        """
        try:
            # Check existing by primary identifier (factor name)
            existing = self.get_by_all(
                name=primary_key,
                group=kwargs.get('group', 'company_share'),
                subgroup=kwargs.get('subgroup', 'return'),
                frequency=kwargs.get('frequency', '1d'),
                factor_type=kwargs.get('factor_type', 'return'),
                data_type=self.mapper.discriminator,
                source=kwargs.get('source', 'market_data')
            )
            if existing:
                return self._to_entity(existing)

            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group', 'company_share'),
                subgroup=kwargs.get('subgroup', 'return'),
                frequency=kwargs.get('frequency', '1d'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'market_data'),
                definition=kwargs.get('definition', f'{self.mapper.discriminator} factor: {primary_key}')
            )
            
            # Use FactorMapper to convert domain entity to ORM model
            orm_factor = self._to_model(domain_factor)
            
            self.session.add(orm_factor)
            #create_or_get dependencies
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
                            frequency=dependency_config.get("frequency", "1d"),
                            data_type=dependency_config.get("data_type"),
                            factor_type=dependency_config.get("factor_type"),
                            source=dependency_config.get("source"),
                            definition=dependency_config.get("definition"),)


                    repo_factor_dependency = self.factory.get_local_repository(FactorDependency)
                    lag = dependency_config.get("parameters", {}).get("lag") if dependency_config.get("parameters") else None
                    repo_factor_dependency._create_or_get(independent_factor = dependency_entity,dependent_factor = self._to_entity(orm_factor), lag=lag)
 
            
            self.session.commit()
            if orm_factor:
                return self._to_entity(orm_factor)
            
        except Exception as e:
            print(f"Error in get_or_create for index future option price return factor {primary_key}: {e}")
            return None

    def get_factor_model(self):
        return self.mapper.get_factor_model()
    
    def get_factor_entity(self):
        return self.mapper.get_factor_entity()
    
    def _to_entity(self, infra_factor) -> Optional[CompanySharePriceReturnFactor]:
        """Convert ORM Factor model to domain CompanySharePriceReturnFactor entity."""
        if not infra_factor:
            return None
        return self.mapper.to_domain(infra_factor)

    def _to_model(self, entity: CompanySharePriceReturnFactor) -> FactorModel:
        """Convert domain CompanySharePriceReturnFactor entity to ORM model."""
        if not entity:
            return None
        return self.mapper.to_orm(entity)

    def _to_domain(self, infra_factor) -> Optional[CompanySharePriceReturnFactor]:
        """Legacy compatibility method."""
        return self._to_entity(infra_factor)

    def get_by_id(self, entity_id: int) -> Optional[CompanySharePriceReturnFactor]:
        """Get company share price return factor by ID."""
        try:
            factor = (
                self.session.query(self.model_class)
                .filter(self.model_class.id == entity_id)
                .first()
            )
            return self._to_domain(factor)
        except Exception as e:
            logger.error(f"Error retrieving company share price return factor by ID {entity_id}: {e}")
            return None

    def get_by_name(self, name: str) -> Optional[CompanySharePriceReturnFactor]:
        """Get company share price return factor by name."""
        try:
            factor = (
                self.session.query(self.model_class)
                .filter(self.model_class.name == name)
                .first()
            )
            return self._to_domain(factor)
        except Exception as e:
            logger.error(f"Error retrieving company share price return factor by name {name}: {e}")
            return None

    def get_all(self) -> list[CompanySharePriceReturnFactor]:
        """Get all company share price return factors."""
        try:
            factors = self.session.query(self.model_class).all()
            return [self._to_domain(factor) for factor in factors]
        except Exception as e:
            logger.error(f"Error retrieving all company share price return factors: {e}")
            return []
        
    def get_by_all(
        self,
        name: str,
        group: str,
        factor_type: Optional[str] = None,
        subgroup: Optional[str] = None,
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
    ):
        """Retrieve a factor matching all provided (non-None) fields."""
        try:
            FactorModel = self.get_factor_model()

            query = self.session.query(FactorModel)

            # Mandatory filters
            query = query.filter(
                FactorModel.name == name,
                FactorModel.group == group,
            )

            # Optional filters
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
            print(f"Error retrieving factor by all attributes: {e}")
            return None

    def add(self, entity: CompanySharePriceReturnFactor) -> Optional[CompanySharePriceReturnFactor]:
        """Add/persist a company share price return factor entity."""
        try:
            new_factor = self._to_model(entity)
            self.session.add(new_factor)
            self.session.commit()
            self.session.refresh(new_factor)
            return self._to_domain(new_factor)
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding company share price return factor: {e}")
            return None

    

    def get_by_group(self, group: str) -> list[CompanySharePriceReturnFactor]:
        """Get company share price return factors by group."""
        try:
            factors = (
                self.session.query(self.model_class)
                .filter(self.model_class.group == group)
                .all()
            )
            return [self._to_domain(factor) for factor in factors]
        except Exception as e:
            logger.error(f"Error retrieving company share price return factors by group {group}: {e}")
            return []

    def get_by_subgroup(self, subgroup: str) -> list[CompanySharePriceReturnFactor]:
        """Get company share price return factors by subgroup."""
        try:
            factors = (
                self.session.query(self.model_class)
                .filter(self.model_class.subgroup == subgroup)
                .all()
            )
            return [self._to_domain(factor) for factor in factors]
        except Exception as e:
            logger.error(f"Error retrieving company share price return factors by subgroup {subgroup}: {e}")
            return []

    def update(self, entity: CompanySharePriceReturnFactor) -> Optional[CompanySharePriceReturnFactor]:
        """Update a company share price return factor entity."""
        try:
            # Convert to model and merge
            model = self._to_model(entity)
            updated_model = self.session.merge(model)
            self.session.commit()
            return self._to_domain(updated_model)
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating company share price return factor: {e}")
            return None

    def delete(self, entity_id: int) -> bool:
        """Delete a company share price return factor entity."""
        try:
            factor = (
                self.session.query(self.model_class)
                .filter(self.model_class.id == entity_id)
                .first()
            )
            if factor:
                self.session.delete(factor)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting company share price return factor with ID {entity_id}: {e}")
            return False