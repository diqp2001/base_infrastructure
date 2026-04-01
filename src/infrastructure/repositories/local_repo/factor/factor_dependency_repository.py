"""
src/infrastructure/repositories/local_repo/factor/factor_dependency_repository.py

Concrete implementation of FactorDependencyPort for local SQLite database.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.domain.entities.factor.factor_dependency import FactorDependency
from src.domain.ports.factor.factor_dependency_port import FactorDependencyPort
from src.infrastructure.models.factor.factor_dependency import FactorDependencyModel
from src.infrastructure.mappers.factor_dependency_mapper import FactorDependencyMapper
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository


class FactorDependencyRepository(BaseLocalRepository[FactorDependency, FactorDependencyModel], FactorDependencyPort):
    """
    Local SQLAlchemy repository implementation for FactorDependency entities.
    
    Follows DDD principles by implementing the FactorDependencyPort interface
    and handling conversion between domain entities and infrastructure models.
    """
    
    def __init__(self, session: Session):
        super().__init__(session)
        self.model_class = FactorDependencyModel
    
    @property
    def entity_class(self):
        """Return the FactorDependency domain entity class."""
        return FactorDependency
    
    def get_by_id(self, entity_id: int) -> Optional[FactorDependency]:
        """Get factor dependency by ID."""
        model = self.get(entity_id)
        return FactorDependencyMapper.model_to_entity(model) if model else None
    
    def get_by_dependent_factor_id(self, dependent_factor_id: int) -> List[FactorDependency]:
        """Get factor dependencies by dependent factor ID."""
        models = self.session.query(FactorDependencyModel).filter(
            FactorDependencyModel.dependent_factor_id == dependent_factor_id
        ).all()
        return FactorDependencyMapper.models_to_entities(models)
    
    def get_by_independent_factor_id(self, independent_factor_id: int) -> List[FactorDependency]:
        """Get factor dependencies by independent factor ID."""
        models = self.session.query(FactorDependencyModel).filter(
            FactorDependencyModel.independent_factor_id == independent_factor_id
        ).all()
        return FactorDependencyMapper.models_to_entities(models)
    
    def get_all(self) -> List[FactorDependency]:
        """Get all factor dependencies."""
        models = self.session.query(FactorDependencyModel).all()
        return FactorDependencyMapper.models_to_entities(models)
    
    def add(self, entity: FactorDependency) -> Optional[FactorDependency]:
        """Add/persist a factor dependency entity."""
        try:
            model = FactorDependencyMapper.entity_to_model(entity)
            persisted_model = super().add(model)
            return FactorDependencyMapper.model_to_entity(persisted_model)
        except Exception:
            self.session.rollback()
            return None
    
    def update(self, entity: FactorDependency) -> Optional[FactorDependency]:
        """Update a factor dependency entity."""
        if not entity.id:
            return None
        
        try:
            updates = {
                'dependent_factor_id': entity.dependent_factor_id,
                'independent_factor_id': entity.independent_factor_id,
                'lag': entity.lag,
                'independent_factor_related_entity_key': entity.independent_factor_related_entity_key
            }
            updated_model = super().update(entity.id, updates)
            return FactorDependencyMapper.model_to_entity(updated_model) if updated_model else None
        except Exception:
            self.session.rollback()
            return None
    
    def delete(self, entity_id: int) -> bool:
        """Delete a factor dependency entity."""
        try:
            return super().delete(entity_id)
        except Exception:
            self.session.rollback()
            return False
    
    def exists(self, dependent_factor_id: int, independent_factor_id: int) -> bool:
        """Check if a dependency relationship exists between two factors."""
        count = self.session.query(FactorDependencyModel).filter(
            and_(
                FactorDependencyModel.dependent_factor_id == dependent_factor_id,
                FactorDependencyModel.independent_factor_id == independent_factor_id
            )
        ).count()
        return count > 0
    
    def _create_or_get(self, independent_factor, dependent_factor, lag=None,independent_factor_related_entity_key=None ) -> Optional[FactorDependency]:
        """
        Create or get a factor dependency relationship.
        
        Args:
            independent_factor: Domain entity of the independent factor
            dependent_factor: Domain entity of the dependent factor
            lag: Optional timedelta for time-based dependency lag
            
        Returns:
            FactorDependency entity or None if creation failed
        """
        try:
            # Extract IDs from domain entities
            independent_factor_id = independent_factor.id if hasattr(independent_factor, 'id') else None
            dependent_factor_id = dependent_factor.id if hasattr(dependent_factor, 'id') else None
            
            if not independent_factor_id or not dependent_factor_id:
                return None
            #independent_factor_entity_id or lag loop parameters
            
                # Fetch existing dependency
            existing_model = self.session.query(FactorDependencyModel).filter(
                and_(
                    FactorDependencyModel.dependent_factor_id == dependent_factor_id,
                    FactorDependencyModel.independent_factor_id == independent_factor_id,
                    FactorDependencyModel.lag == lag,
                    FactorDependencyModel.independent_factor_related_entity_key == independent_factor_related_entity_key
                )
            ).first()
            if existing_model:
                return FactorDependencyMapper.model_to_entity(existing_model) if existing_model else None
            
            # Create new dependency
            dependency_entity = FactorDependency(
                dependent_factor_id=dependent_factor_id,
                independent_factor_id=independent_factor_id,
                lag=lag,
                independent_factor_related_entity_key=independent_factor_related_entity_key
            )
            
            return self.add(dependency_entity)
            
        except Exception as e:
            print(f"Error in _create_or_get factor dependency: {e}")
            self.session.rollback()
            return None