"""
Base repository class for factor entities with common CRUD operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from src.infrastructure.database.settings import get_db


class BaseFactorRepository(ABC):
    """Base repository for all factor entities with common CRUD operations."""
    
    def __init__(self, db_type='sqlite'):
        self.db_type = db_type
        self.db = get_db(db_type)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()

    @abstractmethod
    def get_factor_model(self):
        """Return the factor model class."""
        pass

    @abstractmethod
    def get_factor_value_model(self):
        """Return the factor value model class."""
        pass

    @abstractmethod
    def get_factor_rule_model(self):
        """Return the factor rule model class."""
        pass

    def create_factor(self, **kwargs):
        """Create a new factor."""
        factor_model = self.get_factor_model()
        factor = factor_model(**kwargs)
        
        try:
            self.db.add(factor)
            self.db.commit()
            self.db.refresh(factor)
            return factor
        except Exception as e:
            self.db.rollback()
            print(f"Error creating factor: {e}")
            return None

    def get_by_name(self, name: str):
        """Get factor by name."""
        factor_model = self.get_factor_model()
        try:
            return self.db.query(factor_model).filter(factor_model.name == name).first()
        except Exception as e:
            print(f"Error retrieving factor by name: {e}")
            return None

    def list_all(self) -> List:
        """List all factors."""
        factor_model = self.get_factor_model()
        try:
            return self.db.query(factor_model).all()
        except Exception as e:
            print(f"Error listing all factors: {e}")
            return []

    def get_by_id(self, factor_id: int):
        """Get factor by ID."""
        factor_model = self.get_factor_model()
        try:
            return self.db.query(factor_model).filter(factor_model.id == factor_id).first()
        except Exception as e:
            print(f"Error retrieving factor by ID: {e}")
            return None

    def update_factor(self, factor_id: int, **kwargs):
        """Update factor by ID."""
        factor_model = self.get_factor_model()
        try:
            factor = self.db.query(factor_model).filter(factor_model.id == factor_id).first()
            if factor:
                for key, value in kwargs.items():
                    if hasattr(factor, key):
                        setattr(factor, key, value)
                self.db.commit()
                return factor
            return None
        except Exception as e:
            self.db.rollback()
            print(f"Error updating factor: {e}")
            return None

    def delete_factor(self, factor_id: int) -> bool:
        """Delete factor by ID."""
        factor_model = self.get_factor_model()
        try:
            factor = self.db.query(factor_model).filter(factor_model.id == factor_id).first()
            if factor:
                self.db.delete(factor)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            print(f"Error deleting factor: {e}")
            return False

    def create_factor_value(self, **kwargs):
        """Create a new factor value."""
        factor_value_model = self.get_factor_value_model()
        factor_value = factor_value_model(**kwargs)
        
        try:
            self.db.add(factor_value)
            self.db.commit()
            self.db.refresh(factor_value)
            return factor_value
        except Exception as e:
            self.db.rollback()
            print(f"Error creating factor value: {e}")
            return None

    def get_by_factor_and_date(self, factor_id: int, date_value: date) -> List:
        """Get factor values by factor ID and date."""
        factor_value_model = self.get_factor_value_model()
        try:
            return self.db.query(factor_value_model).filter(
                factor_value_model.factor_id == factor_id,
                factor_value_model.date == date_value
            ).all()
        except Exception as e:
            print(f"Error retrieving factor values by factor and date: {e}")
            return []

    def get_factor_values_by_entity(self, entity_id: int, factor_id: Optional[int] = None) -> List:
        """Get factor values by entity ID, optionally filtered by factor ID."""
        factor_value_model = self.get_factor_value_model()
        try:
            query = self.db.query(factor_value_model).filter(factor_value_model.entity_id == entity_id)
            if factor_id:
                query = query.filter(factor_value_model.factor_id == factor_id)
            return query.all()
        except Exception as e:
            print(f"Error retrieving factor values by entity: {e}")
            return []

    def create_factor_rule(self, **kwargs):
        """Create a new factor rule."""
        factor_rule_model = self.get_factor_rule_model()
        factor_rule = factor_rule_model(**kwargs)
        
        try:
            self.db.add(factor_rule)
            self.db.commit()
            self.db.refresh(factor_rule)
            return factor_rule
        except Exception as e:
            self.db.rollback()
            print(f"Error creating factor rule: {e}")
            return None

    def get_rules_by_factor(self, factor_id: int) -> List:
        """Get rules by factor ID."""
        factor_rule_model = self.get_factor_rule_model()
        try:
            return self.db.query(factor_rule_model).filter(factor_rule_model.factor_id == factor_id).all()
        except Exception as e:
            print(f"Error retrieving rules by factor: {e}")
            return []