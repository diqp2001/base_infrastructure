"""
Infrastructure model for factor.
SQLAlchemy model for domain factor entity.
"""
from sqlalchemy import Column, Integer, String, Text
from src.infrastructure.models import ModelBase as Base
from sqlalchemy.orm import relationship

class FactorModel(Base):
    __tablename__ = 'factors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    group = Column(String(100), nullable=False)
    subgroup = Column(String(100), nullable=True)
    frequency = Column(String(50), nullable=True)
    data_type = Column(String(100), nullable=True)
    source = Column(String(255), nullable=True)
    definition = Column(Text, nullable=True)
    factor_type = Column(String(100), nullable=False, index=True)  # Discriminator for inheritance
    # Relationships
    factor_values = relationship("src.infrastructure.models.factor.factor_value.FactorValueModel",back_populates="factors")

    # Factor dependency relationships
    dependents = relationship(
        "src.infrastructure.models.factor.factor_dependency.FactorDependencyModel",
        foreign_keys="FactorDependencyModel.dependent_factor_id",
        back_populates="dependent_factor"
    )

    dependencies = relationship(
        "src.infrastructure.models.factor.factor_dependency.FactorDependencyModel",
        foreign_keys="FactorDependencyModel.independent_factor_id",
        back_populates="independent_factor"
    )
    __mapper_args__ = {
        'polymorphic_identity': 'factor',
        'polymorphic_on': factor_type
    }



    def __repr__(self):
        return f"<Factor(id={self.id}, name={self.name}, group={self.group})>"


