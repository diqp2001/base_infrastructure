"""
Repository class for CompanyShareFactor entities - mirrors IndexFactorRepository structure.
"""
import os
import logging
from sqlalchemy.orm import Session
from typing import Optional

from src.infrastructure.repositories.mappers.factor.company_share_factor_mapper import CompanyShareFactorMapper
from src.infrastructure.models.factor.factor import FactorModel
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor
from src.domain.ports.factor.company_share_factor_port import CompanyShareFactorPort
from ...base_factor_repository import BaseFactorRepository

logger = logging.getLogger(__name__)


class CompanyShareFactorRepository(BaseFactorRepository, CompanyShareFactorPort):
    """Repository for CompanyShareFactor entities with CRUD operations."""
    
    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper =  CompanyShareFactorMapper()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Factor."""
        return self.mapper.get_factor_model()
    
    @property
    def entity_class(self):
        """Return the domain entity class for CompanyShareFactor."""
        return self.mapper.get_factor_entity()
    

    def get_factor_model(self):
        return self.mapper.get_factor_model()
    
    def get_factor_entity(self):
        return self.mapper.get_factor_entity()
    
    def _to_entity(self, infra_factor) -> Optional[CompanyShareFactor]:
        """Convert ORM Factor model to domain CompanyShareFactor entity."""
        if not infra_factor:
            return None
        return self.mapper.to_domain(infra_factor)

    def _to_model(self, entity: CompanyShareFactor) -> FactorModel:
        """Convert domain CompanyShareFactor entity to ORM model."""
        if not entity:
            return None
        return self.mapper.to_orm(entity)

    def _to_domain(self, infra_factor) -> Optional[CompanyShareFactor]:
        """Legacy compatibility method."""
        return self._to_entity(infra_factor)
    
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs):
        """
        Get or create an 
        
        Args:
            entity_cls: The entity class (not used but required for interface consistency)
            primary_key: Factor name identifier
            **kwargs: Additional parameters for factor creation
            
        Returns:
            Factor entity or None if creation failed
        """
        try:
            # Check existing by primary identifier (factor name)
            existing = self.get_by_all(name =primary_key,
                                       group=kwargs.get('group', 'price'),
                                       subgroup=kwargs.get('subgroup'),
                frequency=kwargs.get('frequency'),
                factor_type=kwargs.get('factor_type', 'company_share_factor'))
            if existing:
                return self._to_entity(existing)
            domain_factor = self.get_factor_entity()(name=primary_key,
                group=kwargs.get('group', 'index'),
                subgroup=kwargs.get('subgroup', 'daily'),
                frequency=kwargs.get('frequency', '1d'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'market_data'),
                definition=kwargs.get('definition', f'{self.mapper.discriminator} factor: {primary_key}')
                )
            
            
            orm_factor = self._to_model(domain_factor)
            
            self.session.add(orm_factor)
            self.session.commit()
            if orm_factor:
                    #print(f"Created new index factor: {created_factor.name} (ID: {created_factor.id})")
                    return self._to_entity(orm_factor) #to_domain
            
        
            
            
        except Exception as e:
            print(f"Error in get_or_create for index factor {primary_key}: {e}")
            return None

    def get_by_id(self, entity_id: int) -> Optional[CompanyShareFactor]:
        """Get company share factor by ID."""
        try:
            factor = (
                self.session.query(self.model_class)
                .filter(self.model_class.id == entity_id)
                .first()
            )
            return self._to_domain(factor)
        except Exception as e:
            logger.error(f"Error retrieving company share factor by ID {entity_id}: {e}")
            return None

    def get_by_name(self, name: str) -> Optional[CompanyShareFactor]:
        """Get company share factor by name."""
        try:
            factor = (
                self.session.query(self.model_class)
                .filter(self.model_class.name == name)
                .first()
            )
            return self._to_domain(factor)
        except Exception as e:
            logger.error(f"Error retrieving company share factor by name {name}: {e}")
            return None

    def get_all(self) -> list[CompanyShareFactor]:
        """Get all company share factors."""
        try:
            factors = self.session.query(self.model_class).all()
            return [self._to_domain(factor) for factor in factors]
        except Exception as e:
            logger.error(f"Error retrieving all company share factors: {e}")
            return []

    def add(self, entity: CompanyShareFactor) -> Optional[CompanyShareFactor]:
        """Add/persist a company share factor entity."""
        try:
            new_factor = self._to_model(entity)
            self.session.add(new_factor)
            self.session.commit()
            self.session.refresh(new_factor)
            return self._to_domain(new_factor)
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding company share factor: {e}")
            return None

    
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

    def get_by_group(self, group: str) -> list[CompanyShareFactor]:
        """Get company share factors by group."""
        try:
            factors = (
                self.session.query(self.model_class)
                .filter(self.model_class.group == group)
                .all()
            )
            return [self._to_domain(factor) for factor in factors]
        except Exception as e:
            logger.error(f"Error retrieving company share factors by group {group}: {e}")
            return []

    def get_by_subgroup(self, subgroup: str) -> list[CompanyShareFactor]:
        """Get company share factors by subgroup."""
        try:
            factors = (
                self.session.query(self.model_class)
                .filter(self.model_class.subgroup == subgroup)
                .all()
            )
            return [self._to_domain(factor) for factor in factors]
        except Exception as e:
            logger.error(f"Error retrieving company share factors by subgroup {subgroup}: {e}")
            return []

    def update(self, entity: CompanyShareFactor) -> Optional[CompanyShareFactor]:
        """Update a company share factor entity."""
        try:
            # Convert to model and merge
            model = self._to_model(entity)
            updated_model = self.session.merge(model)
            self.session.commit()
            return self._to_domain(updated_model)
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating company share factor: {e}")
            return None

    def delete(self, entity_id: int) -> bool:
        """Delete a company share factor entity."""
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
            logger.error(f"Error deleting company share factor with ID {entity_id}: {e}")
            return False