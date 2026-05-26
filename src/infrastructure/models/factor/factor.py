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
class CompanySharePortfolioOptionFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_portfolio_option_factor"
    }


class CompanySharePortfolioOptionPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_portfolio_option_price_factor"
    }


class CompanySharePortfolioOptionPriceReturnFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_portfolio_option_price_return_factor"
    }


class CompanySharePortfolioOptionDeltaFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_portfolio_option_delta_factor"
    }


class CompanySharePortfolioOptionBlackScholesMertonPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_portfolio_option_black_scholes_merton_price_factor"
    }


class CompanySharePortfolioOptionCoxRossRubinsteinPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_portfolio_option_cox_ross_rubinstein_price_factor"
    }


class CompanySharePortfolioOptionHestonPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_portfolio_option_heston_price_factor"
    }


class PortfolioFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "portfolio_factor"
    }


class PortfolioValueFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "portfolio_value_factor"
    }


class PortfolioHoldingValueFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "portfolio_holding_value_factor"
    }


class CompanySharePortfolioOptionHullWhitePriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_portfolio_option_hull_white_price_factor"
    }


class CompanySharePortfolioOptionSABRPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_portfolio_option_sabr_price_factor"
    }


class CompanySharePortfolioOptionBatesPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_portfolio_option_bates_price_factor"
    }


class CompanySharePortfolioOptionDupireLocalVolatilityPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_portfolio_option_dupire_local_volatility_price_factor"
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




# Mid Price Factor Models
class CompanyShareMidPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_mid_price_factor"
    }


class CompanyShareOptionMidPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_mid_price_factor"
    }


# Advanced Options Pricing Models for Company Share Options
class CompanyShareOptionBlackScholesMertonPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_black_scholes_merton_price_factor"
    }


class CompanyShareOptionCoxRossRubinsteinPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_cox_ross_rubinstein_price_factor"
    }


class CompanyShareOptionHestonPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_heston_price_factor"
    }


class CompanyShareOptionHullWhitePriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_hull_white_price_factor"
    }


class CompanyShareOptionSABRPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_sabr_price_factor"
    }


class CompanyShareOptionBatesPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_bates_price_factor"
    }


class CompanyShareOptionDupireLocalVolatilityPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_option_dupire_local_volatility_price_factor"
    }


# Position, Transaction, and Order Factor Models
class CompanySharePositionValueFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_position_value_factor"
    }


class CompanyShareTransactionValueFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_transaction_value_factor"
    }


class CompanyShareOrderQuantityFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_order_quantity_factor"
    }


class CompanyShareOrderPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_order_price_factor"
    }