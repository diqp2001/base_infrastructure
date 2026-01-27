"""
Base abstract mapper for factor entities.
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.infrastructure.models.factor.factor import FactorModel
from src.domain.entities.factor.factor import Factor


class BaseFactorMapper(ABC):
    """Abstract base mapper for factor entities."""
    
    @abstractmethod
    def get_factor_model(self):
        """Return the SQLAlchemy model class."""
        return FactorModel
    
    @abstractmethod
    def get_factor_entity(self):
        """Return the domain entity class."""
        pass
    
    @classmethod
    @abstractmethod
    def to_domain(cls, orm_model: Optional[FactorModel]) -> Optional[Factor]:
        """Convert ORM model to domain entity."""
        pass
    
    @classmethod
    @abstractmethod
    def to_orm(cls, domain_entity: Factor) -> FactorModel:
        """Convert domain entity to ORM model."""
        pass