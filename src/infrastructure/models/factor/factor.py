"""
Infrastructure model for factor.
SQLAlchemy model for domain factor entity.
"""
from sqlalchemy import Column, Integer, String, Text
from src.infrastructure.models import ModelBase as Base


class Factor(Base):
    __tablename__ = 'factors'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    group = Column(String(100), nullable=False)
    subgroup = Column(String(100), nullable=True)
    data_type = Column(String(100), nullable=True)
    source = Column(String(255), nullable=True)
    definition = Column(Text, nullable=True)
    factor_type = Column(String(100), nullable=False)  # Discriminator for inheritance
    
    __mapper_args__ = {
        'polymorphic_identity': 'factor',
        'polymorphic_on': factor_type
    }
    
    def __init__(self, name: str, group: str, subgroup: str = None, data_type: str = None,
                 source: str = None, definition: str = None):
        self.name = name
        self.group = group
        self.subgroup = subgroup
        self.data_type = data_type
        self.source = source
        self.definition = definition
    
    def __repr__(self):
        return f"<Factor(id={self.id}, name={self.name}, group={self.group})>"