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
    data_type = Column(String(100), nullable=True)
    source = Column(String(255), nullable=True)
    definition = Column(Text, nullable=True)
    factor_type = Column(String(100), nullable=False, index=True)  # Discriminator for inheritance
    # Relationships
    factor_values = relationship("src.infrastructure.models.factor.factor_value.FactorValueModel",back_populates="factors")
    __mapper_args__ = {
        'polymorphic_identity': 'factor',
        'polymorphic_on': factor_type
    }
    
    
    
    def __repr__(self):
        return f"<Factor(id={self.id}, name={self.name}, group={self.group})>"


# Polymorphic subclasses for each factor type
class ContinentFactorModel(FactorModel):
    __mapper_args__ = {
        'polymorphic_identity': 'continent',
    }


class CountryFactorModel(FactorModel):
    __mapper_args__ = {
        'polymorphic_identity': 'country',
    }


class FinancialAssetFactorModel(FactorModel):
    __mapper_args__ = {
        'polymorphic_identity': 'financial_asset',
    }


class SecurityFactorModel(FactorModel):
    __mapper_args__ = {
        'polymorphic_identity': 'security',
    }


class IndexFactorModel(FactorModel):
    __mapper_args__ = {
        'polymorphic_identity': 'index',
    }


class CurrencyFactorModel(FactorModel):
    __mapper_args__ = {
        'polymorphic_identity': 'currency',
    }


class EquityFactorModel(FactorModel):
    __mapper_args__ = {
        'polymorphic_identity': 'equity',
    }


class ShareFactorModel(FactorModel):
    __mapper_args__ = {
        'polymorphic_identity': 'share',
    }


class ShareMomentumFactorModel(FactorModel):
    __mapper_args__ = {
        'polymorphic_identity': 'share_momentum',
    }


class ShareTechnicalFactorModel(FactorModel):
    __mapper_args__ = {
        'polymorphic_identity': 'share_technical',
    }


class ShareTargetFactorModel(FactorModel):
    __mapper_args__ = {
        'polymorphic_identity': 'share_target',
    }


class ShareVolatilityFactorModel(FactorModel):
    __mapper_args__ = {
        'polymorphic_identity': 'share_volatility',
    }