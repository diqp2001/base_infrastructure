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

class CompanyShareFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_factor"
    }

class CompanySharePriceReturnFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_price_return_factor"
    }
class IndexFutureFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "index_future_factor"
    }

class IndexFuturePriceReturnFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "index_future_price_return_factor"
    }
class IndexFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "index_factor"
    }
class IndexPriceReturnFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "index_price_return_factor"
    }


class FuturePriceReturnFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "future_price_return_factor"
    }


# Index Future Option Factor Models
class IndexFutureOptionFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "index_future_option_factor"
    }


class IndexFutureOptionPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "index_future_option_price_factor"
    }


class IndexFutureOptionPriceReturnFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "index_future_option_price_return_factor"
    }


class IndexFutureOptionDeltaFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "index_future_option_delta_factor"
    }


# Portfolio Company Share Option Factor Models
class PortfolioCompanyShareOptionFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "portfolio_company_share_option_factor"
    }


class PortfolioCompanyShareOptionPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "portfolio_company_share_option_price_factor"
    }


class PortfolioCompanyShareOptionPriceReturnFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "portfolio_company_share_option_price_return_factor"
    }


class PortfolioCompanyShareOptionDeltaFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "portfolio_company_share_option_delta_factor"
    }


# Company Share Option Factor Models
class CompanyShareOptionFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_factor"
    }


class CompanyShareOptionPriceReturnFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_price_return_factor"
    }


# Additional Company Share Option Factor Models
class CompanyShareOptionDeltaFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_delta_factor"
    }


class CompanyShareOptionGammaFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_gamma_factor"
    }


class CompanyShareOptionPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_price_factor"
    }


class CompanyShareOptionRhoFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_rho_factor"
    }


class CompanyShareOptionVegaFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_vega_factor"
    }


# ETF Share Portfolio Company Share Option Factor Models
class ETFSharePortfolioCompanyShareOptionFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "etf_share_portfolio_company_share_option_factor"
    }


class ETFSharePortfolioCompanyShareOptionDeltaFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "etf_share_portfolio_company_share_option_delta_factor"
    }


class ETFSharePortfolioCompanyShareOptionPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "etf_share_portfolio_company_share_option_price_factor"
    }


class ETFSharePortfolioCompanyShareOptionPriceReturnFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "etf_share_portfolio_company_share_option_price_return_factor"
    }