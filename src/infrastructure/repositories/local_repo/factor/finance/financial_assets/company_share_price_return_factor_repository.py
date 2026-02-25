"""
Repository class for CompanySharePriceReturnFactor entities - mirrors IndexPriceReturnFactorRepository structure.
"""
import os
import logging
from sqlalchemy.orm import Session
from typing import Optional

from src.infrastructure.repositories.mappers.factor.company_share_price_return_factor_mapper import CompanySharePriceReturnFactorMapper
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

    def get_or_create(self, primary_key: str, **kwargs) -> Optional[CompanySharePriceReturnFactor]:
        """
        Get or create a company share price return factor with dependency resolution.
        
        Args:
            primary_key: Factor name identifier
            **kwargs: Additional parameters for factor creation
            
        Returns:
            CompanySharePriceReturnFactor entity or None if creation failed
        """
        try:
            # Check existing by primary identifier (factor name)
            existing = self.get_by_name(primary_key)
            if existing:
                return existing
            
            # Create new factor using base _create_or_get method
            return self._create_or_get(
                name=primary_key,
                group=kwargs.get('group', 'return'),
                subgroup=kwargs.get('subgroup', 'price_return'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'market_data'),
                definition=kwargs.get('definition', f'Company share price return factor: {primary_key}'),
                entity_type=kwargs.get('entity_type', 'CompanySharePriceReturnFactor')
            )
            
        except Exception as e:
            logger.error(f"Error in get_or_create for company share price return factor {primary_key}: {e}")
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