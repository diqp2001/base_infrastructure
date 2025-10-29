"""
Base repository class for factor entities with common CRUD operations.
"""



from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session

from ...base_repository import BaseRepository
from domain.entities.factor.factor import FactorBase as FactorEntity
from domain.entities.factor.factor_value import FactorValue as FactorValueEntity
from domain.entities.factor.factor_rule import FactorRule as FactorRuleEntity

from infrastructure.models.factor.factor_model import (
    Factor as FactorModel,
    FactorValue as FactorValueModel,
    FactorRule as FactorRuleModel,
)

from infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
from infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from infrastructure.repositories.mappers.factor.factor_rule_mapper import FactorRuleMapper

from application.managers.database_managers.database_manager import DatabaseManager


class BaseFactorRepository(BaseRepository[FactorEntity, FactorModel], ABC):
    """Repository managing Factor entities, their values, and rules."""

    def __init__(self, db_type: str = 'sqlite'):
        """Initialize repository with a database type."""
        self.database_manager = DatabaseManager(db_type)
        # Call parent constructor with session
        super().__init__(self.database_manager.session)

    # ----------------------------- Abstract methods -----------------------------
    @abstractmethod
    def get_factor_model(self):
        return FactorModel

    @abstractmethod
    def get_factor_value_model(self):
        return FactorValueModel

    @abstractmethod
    def get_factor_rule_model(self):
        return FactorRuleModel
    
    @property
    def model_class(self):
        """Return the SQLAlchemy factor model class."""
        return self.get_factor_model()
    
    def _to_entity(self, infra_obj) -> Optional[FactorEntity]:
        """Convert ORM model to domain entity."""
        return self._to_domain_factor(infra_obj)
    
    def _to_model(self, entity: FactorEntity) -> FactorModel:
        """Convert domain entity to ORM model."""
        FactorModel = self.get_factor_model()
        model = FactorModel(
            name=entity.name,
            group=entity.group,
            subgroup=entity.subgroup,
            data_type=entity.data_type,
            source=entity.source,
            definition=entity.definition
        )
        if hasattr(entity, 'id') and entity.id is not None:
            model.id = entity.id
        return model

    # ----------------------------- Mappers -----------------------------
    def _to_domain_factor(self, infra_obj) -> Optional[FactorEntity]:
        """Convert ORM factor object to domain entity."""
        if not infra_obj:
            return None
        
        factor_entity = FactorEntity(
            name=infra_obj.name,
            group=infra_obj.group,
            subgroup=infra_obj.subgroup,
            data_type=infra_obj.data_type,
            source=infra_obj.source,
            definition=infra_obj.definition,
            factor_id=infra_obj.id
        )

        return factor_entity
        

    def _to_domain_value(self, infra_obj) -> Optional[FactorValueEntity]:
        """Convert ORM factor value object to domain entity."""
        if not infra_obj:
            return None
        return FactorValueEntity(
            id=infra_obj.id,
            factor_id=infra_obj.factor_id,
            entity_id=infra_obj.entity_id,
            date=infra_obj.date,
            value=infra_obj.value
        )

    def _to_domain_rule(self, infra_obj) -> Optional[FactorRuleEntity]:
        """Convert ORM factor rule object to domain entity."""
        if not infra_obj:
            return None
        return FactorRuleEntity(
            id=infra_obj.id,
            factor_id=infra_obj.factor_id,
            condition=infra_obj.condition,
            rule_type=infra_obj.rule_type,
            method_ref=infra_obj.method_ref
        )

    # ----------------------------- CRUD: Factors -----------------------------
    def create_factor(self, domain_factor: FactorEntity) -> Optional[FactorEntity]:
        """Add a new factor to the database using sequential ID generation."""
        try:
            FactorModel = self.get_factor_model()
            
            # Use sequential ID generation if factor doesn't have an ID
            if not hasattr(domain_factor, 'id') or domain_factor.id is None:
                next_id = self._get_next_available_factor_id()
                domain_factor.id = next_id
            
            # Create ORM object directly using the specific model
            orm_factor = FactorModel(
                id=domain_factor.id,  # Use sequential ID
                name=domain_factor.name,
                group=domain_factor.group,
                subgroup=domain_factor.subgroup,
                data_type=domain_factor.data_type,
                source=domain_factor.source,
                definition=domain_factor.definition
            )
            self.session.add(orm_factor)
            self.session.commit()
            return self._to_domain_factor(orm_factor)
        except Exception as e:
            self.session.rollback()
            print(f"Error creating factor: {e}")
            return None

    def get_by_name(self, name: str) -> Optional[FactorEntity]:
        """Retrieve a factor by its name."""
        try:
            FactorModel = self.get_factor_model()
            factor = self.session.query(FactorModel).filter(FactorModel.name == name).first()
            return self._to_domain_factor(factor)
        except Exception as e:
            print(f"Error retrieving factor by name: {e}")
            return None

    def get_by_id(self, factor_id: int) -> Optional[FactorEntity]:
        """Retrieve a factor by its ID."""
        try:
            FactorModel = self.get_factor_model()
            factor = self.session.query(FactorModel).filter(FactorModel.id == factor_id).first()
            return self._to_domain_factor(factor)
        except Exception as e:
            print(f"Error retrieving factor by ID: {e}")
            return None

    def list_all(self) -> List[FactorEntity]:
        """List all factors."""
        try:
            FactorModel = self.get_factor_model()
            factors = self.session.query(FactorModel).all()
            return [self._to_domain_factor(f) for f in factors]
        except Exception as e:
            print(f"Error listing factors: {e}")
            return []

    def update_factor(self, factor_id: int, **kwargs) -> Optional[FactorEntity]:
        """Update a factor's properties."""
        try:
            FactorModel = self.get_factor_model()
            factor = self.session.query(FactorModel).filter(FactorModel.id == factor_id).first()
            if not factor:
                return None
            for key, value in kwargs.items():
                if hasattr(factor, key):
                    setattr(factor, key, value)
            self.session.commit()
            return self._to_domain_factor(factor)
        except Exception as e:
            self.session.rollback()
            print(f"Error updating factor: {e}")
            return None

    def delete_factor(self, factor_id: int) -> bool:
        """Delete a factor by ID."""
        try:
            FactorModel = self.get_factor_model()
            factor = self.session.query(FactorModel).filter(FactorModel.id == factor_id).first()
            if not factor:
                return False
            self.session.delete(factor)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"Error deleting factor: {e}")
            return False

    # ----------------------------- CRUD: Factor Values -----------------------------
    def create_factor_value(self, domain_value: FactorValueEntity) -> Optional[FactorValueEntity]:
        """Add a new factor value."""
        try:
            FactorValueModel = self.get_factor_value_model()
            # Create ORM object directly using the specific model
            orm_value = FactorValueModel(
                factor_id=domain_value.factor_id,
                entity_id=domain_value.entity_id,
                date=domain_value.date,
                value=domain_value.value
            )
            self.session.add(orm_value)
            self.session.commit()
            return self._to_domain_value(orm_value)
        except Exception as e:
            self.session.rollback()
            print(f"Error creating factor value: {e}")
            return None

    def get_by_factor_and_date(self, factor_id: int, date_value: date) -> List[FactorValueEntity]:
        """Get all values for a factor on a specific date."""
        try:
            FactorValueModel = self.get_factor_value_model()
            values = (
                self.session.query(FactorValueModel)
                .filter(FactorValueModel.factor_id == factor_id, FactorValueModel.date == date_value)
                .all()
            )
            return [self._to_domain_value(v) for v in values]
        except Exception as e:
            print(f"Error retrieving factor values: {e}")
            return []

    def get_factor_values_by_entity(self, entity_id: int, factor_id: Optional[int] = None) -> List[FactorValueEntity]:
        """Get all factor values for a given entity."""
        try:
            FactorValueModel = self.get_factor_value_model()
            query = self.session.query(FactorValueModel).filter(FactorValueModel.entity_id == entity_id)
            if factor_id:
                query = query.filter(FactorValueModel.factor_id == factor_id)
            values = query.all()
            return [self._to_domain_value(v) for v in values]
        except Exception as e:
            print(f"Error retrieving factor values by entity: {e}")
            return []

    def get_factor_values(self, factor_id: int, entity_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[FactorValueEntity]:
        """
        Get factor values for a specific factor and entity within a date range.
        
        Args:
            factor_id: ID of the factor
            entity_id: ID of the entity
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
            
        Returns:
            List of factor value entities within the date range
        """
        try:
            from datetime import datetime
            
            FactorValueModel = self.get_factor_value_model()
            query = self.session.query(FactorValueModel).filter(
                FactorValueModel.factor_id == factor_id,
                FactorValueModel.entity_id == entity_id
            )
            
            # Add date filters if provided
            if start_date:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                query = query.filter(FactorValueModel.date >= start_date_obj)
            
            if end_date:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
                query = query.filter(FactorValueModel.date <= end_date_obj)
            
            # Order by date
            query = query.order_by(FactorValueModel.date)
            
            values = query.all()
            return [self._to_domain_value(v) for v in values]
            
        except Exception as e:
            print(f"Error retrieving factor values: {e}")
            return []

    def get_factors_by_groups(self, groups: List[str]) -> List[FactorEntity]:
        """
        Get factors filtered by specific groups.
        
        Args:
            groups: List of group names to filter by (e.g., ['price', 'momentum', 'technical'])
            
        Returns:
            List of factor entities matching the specified groups
        """
        try:
            FactorModel = self.get_factor_model()
            query = self.session.query(FactorModel)
            
            if groups:
                # Filter by groups using IN clause
                query = query.filter(FactorModel.group.in_(groups))
            
            # Order by group and name for consistent results
            query = query.order_by(FactorModel.group, FactorModel.name)
            
            factors = query.all()
            return [self._to_domain(factor) for factor in factors]
            
        except Exception as e:
            print(f"Error retrieving factors by groups: {e}")
            return []

    def factor_value_exists(self, factor_id: int, entity_id: int, date_value: date) -> bool:
        """
        Check if a factor value already exists for the given factor_id, entity_id, and date.
        
        Args:
            factor_id: ID of the factor
            entity_id: ID of the entity
            date_value: Date of the value
            
        Returns:
            bool: True if the value exists, False otherwise
        """
        try:
            FactorValueModel = self.get_factor_value_model()
            existing_value = (
                self.session.query(FactorValueModel)
                .filter(
                    FactorValueModel.factor_id == factor_id,
                    FactorValueModel.entity_id == entity_id,
                    FactorValueModel.date == date_value
                )
                .first()
            )
            return existing_value is not None
        except Exception as e:
            print(f"Error checking factor value existence: {e}")
            return False

    def get_existing_value_dates(self, factor_id: int, entity_id: int) -> set:
        """
        Get all existing dates for which factor values exist for a specific factor and entity.
        
        Args:
            factor_id: ID of the factor
            entity_id: ID of the entity
            
        Returns:
            set: Set of dates that already have factor values
        """
        try:
            FactorValueModel = self.get_factor_value_model()
            dates = (
                self.session.query(FactorValueModel.date)
                .filter(
                    FactorValueModel.factor_id == factor_id,
                    FactorValueModel.entity_id == entity_id
                )
                .all()
            )
            return {date_tuple[0] for date_tuple in dates}
        except Exception as e:
            print(f"Error retrieving existing value dates: {e}")
            return set()

    # ----------------------------- CRUD: Factor Rules -----------------------------
    def create_factor_rule(self, domain_rule: FactorRuleEntity) -> Optional[FactorRuleEntity]:
        """Add a new rule for a factor."""
        try:
            FactorRuleModel = self.get_factor_rule_model()
            # Create ORM object directly using the specific model
            orm_rule = FactorRuleModel(
                factor_id=domain_rule.factor_id,
                condition=domain_rule.condition,
                rule_type=domain_rule.rule_type,
                method_ref=domain_rule.method_ref
            )
            self.session.add(orm_rule)
            self.session.commit()
            return self._to_domain_rule(orm_rule)
        except Exception as e:
            self.session.rollback()
            print(f"Error creating factor rule: {e}")
            return None

    def get_rules_by_factor(self, factor_id: int) -> List[FactorRuleEntity]:
        """Retrieve all rules for a given factor."""
        try:
            FactorRuleModel = self.get_factor_rule_model()
            rules = self.session.query(FactorRuleModel).filter(FactorRuleModel.factor_id == factor_id).all()
            return [self._to_domain_rule(r) for r in rules]
        except Exception as e:
            print(f"Error retrieving rules: {e}")
            return []

    def get_rule_by_factor_and_condition(self, factor_id: int, condition: str) -> Optional[FactorRuleEntity]:
        """Check if a rule already exists for a factor with a specific condition."""
        try:
            FactorRuleModel = self.get_factor_rule_model()
            rule = (
                self.session.query(FactorRuleModel)
                .filter(FactorRuleModel.factor_id == factor_id, FactorRuleModel.condition == condition)
                .first()
            )
            return self._to_domain_rule(rule)
        except Exception as e:
            print(f"Error checking for existing rule: {e}")
            return None

    def _get_next_available_factor_id(self) -> int:
        """
        Get the next available ID for factor creation.
        Returns the next sequential ID based on existing database records.
        
        Returns:
            int: Next available ID (defaults to 1 if no records exist)
        """
        try:
            FactorModel = self.get_factor_model()
            max_id_result = self.session.query(FactorModel.id).order_by(FactorModel.id.desc()).first()
            
            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist
                
        except Exception as e:
            print(f"Warning: Could not determine next available factor ID: {str(e)}")
            return 1  # Default to 1 if query fails

    # ----------------------------- Standard CRUD Interface -----------------------------
    def create(self, entity: FactorEntity) -> FactorEntity:
        """Create new factor entity in database"""
        return self.create_factor(entity)

    def update(self, entity_id: int, updates: dict) -> Optional[FactorEntity]:
        """Update factor entity with new data"""
        return self.update_factor(entity_id, **updates)

    def delete(self, entity_id: int) -> bool:
        """Delete factor entity by ID"""
        return self.delete_factor(entity_id)

    # ----------------------------- Convenience Methods -----------------------------
    def add_factor(self, name: str, group: str, subgroup: str, data_type: str, source: str, definition: str) -> Optional[FactorEntity]:
        """
        Convenience method to add a new factor.
        
        Args:
            name: Factor name
            group: Factor group
            subgroup: Factor subgroup  
            data_type: Data type (e.g., 'numeric', 'string')
            source: Data source
            definition: Factor definition/description
        
        Returns:
            Created factor entity or None if failed
        """
        from decimal import Decimal
        
        domain_factor = FactorEntity(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition
        )
        return self.create_factor(domain_factor)

    def add_factor_value(self, factor_id: int, entity_id: int, date: date, value) -> Optional[FactorValueEntity]:
        """
        Convenience method to add a new factor value.
        
        Args:
            factor_id: ID of the factor
            entity_id: ID of the entity
            date: Date of the value
            value: Factor value (will be converted to Decimal)
        
        Returns:
            Created factor value entity or None if failed
        """
        from decimal import Decimal
        
        # Convert value to Decimal for financial precision
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
            
        domain_value = FactorValueEntity(
            id=None,
            factor_id=factor_id,
            entity_id=entity_id,
            date=date,
            value=value
        )
        return self.create_factor_value(domain_value)

    def add_factor_rule(self, factor_id: int, condition: str, rule_type: str, method_ref: Optional[str] = None) -> Optional[FactorRuleEntity]:
        """
        Convenience method to add a new factor rule.
        
        Args:
            factor_id: ID of the factor
            condition: Rule condition
            rule_type: Type of rule (e.g., 'validation', 'transformation')
            method_ref: Reference to validation/transformation method
        
        Returns:
            Created factor rule entity or None if failed
        """
        domain_rule = FactorRuleEntity(
            id=None,
            factor_id=factor_id,
            condition=condition,
            rule_type=rule_type,
            method_ref=method_ref
        )
        return self.create_factor_rule(domain_rule)
