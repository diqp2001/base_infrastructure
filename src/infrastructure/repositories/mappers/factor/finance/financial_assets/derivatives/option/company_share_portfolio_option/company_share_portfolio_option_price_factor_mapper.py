"""
Mapper for CompanySharePortfolioOptionPriceFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import CompanySharePortfolioOptionPriceFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_price_factor import CompanySharePortfolioOptionPriceFactor
from ......base_factor_mapper import BaseFactorMapper


class CompanySharePortfolioOptionPriceFactorMapper(BaseFactorMapper):
    """Mapper for CompanySharePortfolioOptionPriceFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'company_share_portfolio_option'
    
    @property
    def model_class(self):
        return CompanySharePortfolioOptionPriceFactorModel
    
    def get_factor_model(self):
        return CompanySharePortfolioOptionPriceFactorModel
    
    def get_factor_entity(self):
        return CompanySharePortfolioOptionPriceFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[CompanySharePortfolioOptionPriceFactorModel]) -> Optional[CompanySharePortfolioOptionPriceFactor]:
        """Convert ORM model to CompanySharePortfolioOptionPriceFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanySharePortfolioOptionPriceFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    @classmethod
    def to_orm(cls, domain_entity: CompanySharePortfolioOptionPriceFactor):
        """Convert CompanySharePortfolioOptionPriceFactor domain entity to ORM model."""
        return CompanySharePortfolioOptionPriceFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )