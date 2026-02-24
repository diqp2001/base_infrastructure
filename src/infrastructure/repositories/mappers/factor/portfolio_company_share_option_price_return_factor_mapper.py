"""
Mapper for PortfolioCompanyShareOptionPriceReturnFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import PortfolioCompanyShareOptionPriceReturnFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_price_return_factor import PortfolioCompanyShareOptionPriceReturnFactor
from .base_factor_mapper import BaseFactorMapper


class PortfolioCompanyShareOptionPriceReturnFactorMapper(BaseFactorMapper):
    """Mapper for PortfolioCompanyShareOptionPriceReturnFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'portfolio_company_share_option_price_return_factor'
    
    @property
    def model_class(self):
        return PortfolioCompanyShareOptionPriceReturnFactorModel
    
    def get_factor_model(self):
        return PortfolioCompanyShareOptionPriceReturnFactorModel
    
    def get_factor_entity(self):
        return PortfolioCompanyShareOptionPriceReturnFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[PortfolioCompanyShareOptionPriceReturnFactorModel]) -> Optional[PortfolioCompanyShareOptionPriceReturnFactor]:
        """Convert ORM model to PortfolioCompanyShareOptionPriceReturnFactor domain entity."""
        if not orm_model:
            return None
        
        return PortfolioCompanyShareOptionPriceReturnFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
            current_price=getattr(orm_model, 'current_price', None),
            previous_price=getattr(orm_model, 'previous_price', None),
            underlying_symbol=getattr(orm_model, 'underlying_symbol', None)
        )
    
    @classmethod
    def to_orm(cls, domain_entity: PortfolioCompanyShareOptionPriceReturnFactor):
        """Convert PortfolioCompanyShareOptionPriceReturnFactor domain entity to ORM model."""
        return PortfolioCompanyShareOptionPriceReturnFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )