"""
Mapper for PortfolioCompanyShareOptionPriceFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import PortfolioCompanyShareOptionPriceFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_price_factor import PortfolioCompanyShareOptionPriceFactor
from .base_factor_mapper import BaseFactorMapper


class PortfolioCompanyShareOptionPriceFactorMapper(BaseFactorMapper):
    """Mapper for PortfolioCompanyShareOptionPriceFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'portfolio_company_share_option_price_factor'
    
    @property
    def model_class(self):
        return PortfolioCompanyShareOptionPriceFactorModel
    
    def get_factor_model(self):
        return PortfolioCompanyShareOptionPriceFactorModel
    
    def get_factor_entity(self):
        return PortfolioCompanyShareOptionPriceFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[PortfolioCompanyShareOptionPriceFactorModel]) -> Optional[PortfolioCompanyShareOptionPriceFactor]:
        """Convert ORM model to PortfolioCompanyShareOptionPriceFactor domain entity."""
        if not orm_model:
            return None
        
        return PortfolioCompanyShareOptionPriceFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
            stock_price=getattr(orm_model, 'stock_price', None),
            strike_price=getattr(orm_model, 'strike_price', None),
            multiplier=getattr(orm_model, 'multiplier', None),
            underlying_symbol=getattr(orm_model, 'underlying_symbol', None)
        )
    
    @classmethod
    def to_orm(cls, domain_entity: PortfolioCompanyShareOptionPriceFactor):
        """Convert PortfolioCompanyShareOptionPriceFactor domain entity to ORM model."""
        return PortfolioCompanyShareOptionPriceFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )