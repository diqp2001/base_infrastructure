"""
Mapper for CompanySharePortfolioOptionSABRPriceFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import CompanySharePortfolioOptionSABRPriceFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_sabr_price_factor import CompanySharePortfolioOptionSABRPriceFactor
from ......base_factor_mapper import BaseFactorMapper


class CompanySharePortfolioOptionSABRPriceFactorMapper(BaseFactorMapper):
    """Mapper for CompanySharePortfolioOptionSABRPriceFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'company_share_portfolio_option'
    
    @property
    def model_class(self):
        return CompanySharePortfolioOptionSABRPriceFactorModel
    
    def get_factor_model(self):
        return CompanySharePortfolioOptionSABRPriceFactorModel
    
    def get_factor_entity(self):
        return CompanySharePortfolioOptionSABRPriceFactor
    
    def to_domain(self, orm_model: Optional[CompanySharePortfolioOptionSABRPriceFactorModel]) -> Optional[CompanySharePortfolioOptionSABRPriceFactor]:
        """Convert ORM model to CompanySharePortfolioOptionSABRPriceFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanySharePortfolioOptionSABRPriceFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    def to_orm(self, domain_entity: CompanySharePortfolioOptionSABRPriceFactor) -> CompanySharePortfolioOptionSABRPriceFactorModel:
        """Convert CompanySharePortfolioOptionSABRPriceFactor domain entity to ORM model."""
        return CompanySharePortfolioOptionSABRPriceFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )