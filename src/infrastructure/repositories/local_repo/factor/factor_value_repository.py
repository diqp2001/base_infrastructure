# Factor Value Local Repository
# Mirrors src/infrastructure/models/factor/factor_value.py

from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session

from src.domain.ports.factor.factor_value_port import FactorValuePort
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.domain.entities.factor.factor_value import FactorValue
from src.infrastructure.models.factor.factor_value import FactorValueModel as FactorValueModel
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper


class FactorValueRepository(BaseLocalRepository, FactorValuePort):
    """Local repository for factor value model"""
    
    def __init__(self, session: Session, factory, mapper: FactorValueMapper = None):
        """Initialize FactorValueRepository with database session."""
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or FactorValueMapper()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for FactorValue."""
        return FactorValueModel
    @property
    def entity_class(self):
        """Return the SQLAlchemy model class for FactorValue."""
        return FactorValue
    
    def _to_entity(self, model: FactorValueModel) -> FactorValue:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        return self.mapper.to_domain(model)
    
    def _to_model(self, entity: FactorValue) -> FactorValueModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        return self.mapper.to_orm(entity)
            
    
    def get_by_id(self, entity_id: int) -> Optional[FactorValue]:
        """Get factor value by ID."""
        model = self.session.query(FactorValueModel).filter(
            FactorValueModel.id == entity_id
        ).first()
        return self._to_entity(model)
    
    def get_by_name(self, name: str) -> Optional[FactorValue]:
        """Get factor value by name (not applicable for factor values)."""
        # Factor values don't have names, return None
        return None
    
    def get_by_group(self, group: str) -> List[FactorValue]:
        """Get factor values by group (not applicable for factor values)."""
        # Factor values don't have groups, return empty list
        return []
    
    def get_by_subgroup(self, subgroup: str) -> List[FactorValue]:
        """Get factor values by subgroup (not applicable for factor values)."""
        # Factor values don't have subgroups, return empty list
        return []
    
    def get_all(self) -> List[FactorValue]:
        """Get all factor values."""
        models = self.session.query(FactorValueModel).all()
        return [self._to_entity(model) for model in models]
    
    def add(self, entity: FactorValue) -> Optional[FactorValue]:
        """Add/persist a factor value entity."""
        try:
            model = self._to_model(entity)
            self.session.add(model)
            self.session.commit()
            return self._to_entity(model)
        except Exception as e:
            print(f"Error adding factor value: {e}")
            self.session.rollback()
            return None
    
    def update(self, entity: FactorValue) -> Optional[FactorValue]:
        """Update a factor value entity."""
        try:
            model = self.session.query(FactorValueModel).filter(
                FactorValueModel.id == entity.id
            ).first()
            
            if not model:
                return None
            
            model.factor_id = entity.factor_id
            model.entity_id = entity.entity_id
            model.date = entity.date
            model.value = entity.value
            
            self.session.commit()
            return self._to_entity(model)
        except Exception as e:
            print(f"Error updating factor value: {e}")
            self.session.rollback()
            return None
    
    def delete(self, entity_id: int) -> bool:
        """Delete a factor value entity."""
        try:
            model = self.session.query(FactorValueModel).filter(
                FactorValueModel.id == entity_id
            ).first()
            
            if not model:
                return False
            
            self.session.delete(model)
            self.session.commit()
            return True
        except Exception as e:
            print(f"Error deleting factor value: {e}")
            self.session.rollback()
            return False
    
    def get_all_dates_by_id_entity_id(self, factor_id: int, entity_id: int) -> List[str]:
        """Get all dates for a specific factor and entity combination."""
        try:
            dates = self.session.query(FactorValueModel.date).filter(
                FactorValueModel.factor_id == factor_id,
                FactorValueModel.entity_id == entity_id
            ).all()
            
            return [str(date_tuple[0]) for date_tuple in dates]
        except Exception as e:
            print(f"Error getting dates for factor {factor_id} and entity {entity_id}: {e}")
            return []
    
    def get_by_factor_entity_date(self, factor_id: int, entity_id: int, date_str: str) -> Optional[FactorValue]:
        """Get factor value by factor ID, entity ID, and date."""
        try:
            # Convert date string to date object
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            model = self.session.query(FactorValueModel).filter(
                FactorValueModel.factor_id == factor_id,
                FactorValueModel.entity_id == entity_id,
                FactorValueModel.date == date_obj
            ).first()
            
            return self._to_entity(model)
        except Exception as e:
            print(f"Error getting factor value for factor {factor_id}, entity {entity_id}, date {date_str}: {e}")
            return None
    
    def _create_or_get(self, factor_id: int, entity_id: int, date: date, value: str) -> Optional[FactorValue]:
        """Create factor value entity if it doesn't exist, otherwise return existing."""
        # Check if entity already exists by factor_id, entity_id, and date
        existing = self.get_by_factor_entity_date(factor_id, entity_id, str(date))
        if existing:
            return existing
        
        try:
            # Get next available ID
            next_id = self._get_next_available_id()
            
            # Create new factor value entity
            factor_value = FactorValue(
                id=next_id,
                factor_id=factor_id,
                entity_id=entity_id,
                date=date,
                value=value
            )
            
            # Add to database
            return self.add(factor_value)
            
        except Exception as e:
            print(f"Error creating factor value for factor {factor_id}, entity {entity_id}: {str(e)}")
            return None

    def get_or_create(self, primary_key: str, **kwargs) -> Optional[FactorValue]:
        """
        Get or create a factor value with dependency resolution.
        
        Args:
            primary_key: Composite key "factor_id_entity_id_date"
            **kwargs: Additional parameters for factor value creation
            
        Returns:
            FactorValue entity or None if creation failed
        """
        try:
            # Parse composite primary key - expecting format "factor_id_entity_id_date"
            parts = primary_key.split('_', 2)
            if len(parts) != 3:
                print(f"Invalid primary key format: {primary_key}. Expected format: 'factor_id_entity_id_date'")
                return None
                
            factor_id = int(parts[0])
            entity_id = int(parts[1])
            date_str = parts[2]
            
            # Check existing by composite key
            existing = self.get_by_factor_entity_date(factor_id, entity_id, date_str)
            if existing:
                return existing
            
            # Create new factor value using base _create_or_get method
            from datetime import datetime
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            return self._create_or_get(
                factor_id=factor_id,
                entity_id=entity_id,
                date=date_obj,
                value=kwargs.get('value', '0.0')
            )
            
        except Exception as e:
            print(f"Error in get_or_create for factor value {primary_key}: {e}")
            return None