"""
Mapper for ETFSharePortfolioCompanyShareOptionFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import ETFSharePortfolioCompanyShareOptionFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_portfolio_company_share_option.etf_share_portfolio_company_share_option_factor import ETFSharePortfolioCompanyShareOptionFactor
from .base_factor_mapper import BaseFactorMapper


class ETFSharePortfolioCompanyShareOptionFactorMapper(BaseFactorMapper):
    """Mapper for ETFSharePortfolioCompanyShareOptionFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'etf_share_portfolio_company_share_option_factor'
    
    @property
    def model_class(self):
        return ETFSharePortfolioCompanyShareOptionFactorModel
    
    def get_factor_model(self):
        return ETFSharePortfolioCompanyShareOptionFactorModel
    
    def get_factor_entity(self):
        return ETFSharePortfolioCompanyShareOptionFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[ETFSharePortfolioCompanyShareOptionFactorModel]) -> Optional[ETFSharePortfolioCompanyShareOptionFactor]:
        """Convert ORM model to ETFSharePortfolioCompanyShareOptionFactor domain entity."""
        if not orm_model:
            return None
        
        return ETFSharePortfolioCompanyShareOptionFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
            stock_price=getattr(orm_model, 'stock_price', None),
            strike_price=getattr(orm_model, 'strike_price', None),
            volatility=getattr(orm_model, 'volatility', None),
            time_to_expiry=getattr(orm_model, 'time_to_expiry', None),
            underlying_symbol=getattr(orm_model, 'underlying_symbol', None)
        )
    
    @classmethod
    def to_orm(cls, domain_entity: ETFSharePortfolioCompanyShareOptionFactor):
        """Convert ETFSharePortfolioCompanyShareOptionFactor domain entity to ORM model."""
        return ETFSharePortfolioCompanyShareOptionFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )