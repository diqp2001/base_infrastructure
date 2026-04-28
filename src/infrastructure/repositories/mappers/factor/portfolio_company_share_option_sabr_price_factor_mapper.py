"""
Mapper for PortfolioCompanyShareOptionSABRPriceFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import PortfolioCompanyShareOptionSABRPriceFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_sabr_price_factor import PortfolioCompanyShareOptionSABRPriceFactor
from .base_factor_mapper import BaseFactorMapper


class PortfolioCompanyShareOptionSABRPriceFactorMapper(BaseFactorMapper):
    """Mapper for PortfolioCompanyShareOptionSABRPriceFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'portfolio_company_share_option'
    
    @property
    def model_class(self):
        return PortfolioCompanyShareOptionSABRPriceFactorModel
    
    def get_factor_model(self):
        return PortfolioCompanyShareOptionSABRPriceFactorModel
    
    def get_factor_entity(self):
        return PortfolioCompanyShareOptionSABRPriceFactor
    
    def to_domain(self, orm_model: Optional[PortfolioCompanyShareOptionSABRPriceFactorModel]) -> Optional[PortfolioCompanyShareOptionSABRPriceFactor]:
        """Convert ORM model to PortfolioCompanyShareOptionSABRPriceFactor domain entity."""
        if not orm_model:
            return None
        
        return PortfolioCompanyShareOptionSABRPriceFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    def to_orm(self, domain_entity: PortfolioCompanyShareOptionSABRPriceFactor) -> PortfolioCompanyShareOptionSABRPriceFactorModel:
        """Convert PortfolioCompanyShareOptionSABRPriceFactor domain entity to ORM model."""
        return PortfolioCompanyShareOptionSABRPriceFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )