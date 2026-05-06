"""
Mapper for CompanySharePortfolioOptionPriceReturnFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import CompanySharePortfolioOptionPriceReturnFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_price_return_factor import CompanySharePortfolioOptionPriceReturnFactor
from ......base_factor_mapper import BaseFactorMapper


class CompanySharePortfolioOptionPriceReturnFactorMapper(BaseFactorMapper):
    """Mapper for CompanySharePortfolioOptionPriceReturnFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'company_share_portfolio_option'
    
    @property
    def model_class(self):
        return CompanySharePortfolioOptionPriceReturnFactorModel
    
    def get_factor_model(self):
        return CompanySharePortfolioOptionPriceReturnFactorModel
    
    def get_factor_entity(self):
        return CompanySharePortfolioOptionPriceReturnFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[CompanySharePortfolioOptionPriceReturnFactorModel]) -> Optional[CompanySharePortfolioOptionPriceReturnFactor]:
        """Convert ORM model to CompanySharePortfolioOptionPriceReturnFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanySharePortfolioOptionPriceReturnFactor(
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
    def to_orm(cls, domain_entity: CompanySharePortfolioOptionPriceReturnFactor):
        """Convert CompanySharePortfolioOptionPriceReturnFactor domain entity to ORM model."""
        return CompanySharePortfolioOptionPriceReturnFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )