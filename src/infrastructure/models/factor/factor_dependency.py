"""
Infrastructure model for factor dependency.
SQLAlchemy model for domain FactorDependency entity.
"""
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class FactorDependencyModel(Base):
    __tablename__ = 'factor_dependencies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dependent_factor_id = Column(Integer, ForeignKey('factors.id'), nullable=False)
    independent_factor_id = Column(Integer, ForeignKey('factors.id'), nullable=False)
    
    # Relationships to FactorModel
    dependent_factor = relationship(
        "src.infrastructure.models.factor.factor.FactorModel",
        foreign_keys=[dependent_factor_id],
        back_populates="dependents"
    )
    
    independent_factor = relationship(
        "src.infrastructure.models.factor.factor.FactorModel", 
        foreign_keys=[independent_factor_id],
        back_populates="dependencies"
    )
    
    def __repr__(self):
        return (f"<FactorDependency(id={self.id}, "
                f"dependent_factor_id={self.dependent_factor_id}, "
                f"independent_factor_id={self.independent_factor_id})>")