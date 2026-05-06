"""
Mapper for CompanySharePortfolioOptionFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import CompanySharePortfolioOptionFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_factor import CompanySharePortfolioOptionFactor
from ......base_factor_mapper import BaseFactorMapper


class CompanySharePortfolioOptionFactorMapper(BaseFactorMapper):
    """Mapper for CompanySharePortfolioOptionFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'company_share_portfolio_option'
    
    @property
    def model_class(self):
        return CompanySharePortfolioOptionFactorModel
    
    def get_factor_model(self):
        return CompanySharePortfolioOptionFactorModel
    
    def get_factor_entity(self):
        return CompanySharePortfolioOptionFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[CompanySharePortfolioOptionFactorModel]) -> Optional[CompanySharePortfolioOptionFactor]:
        """Convert ORM model to CompanySharePortfolioOptionFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanySharePortfolioOptionFactor(
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
    def to_orm(cls, domain_entity: CompanySharePortfolioOptionFactor):
        """Convert CompanySharePortfolioOptionFactor domain entity to ORM model."""
        return CompanySharePortfolioOptionFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )