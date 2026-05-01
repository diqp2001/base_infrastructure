"""
Mapper for PortfolioCompanyShareOptionFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import PortfolioCompanyShareOptionFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option_portfolio.company_share_option_portfolio_factor import CompanyShareOptionPortfolioFactor
from .base_factor_mapper import BaseFactorMapper


class PortfolioCompanyShareOptionFactorMapper(BaseFactorMapper):
    """Mapper for PortfolioCompanyShareOptionFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'portfolio_company_share_option'
    
    @property
    def model_class(self):
        return PortfolioCompanyShareOptionFactorModel
    
    def get_factor_model(self):
        return PortfolioCompanyShareOptionFactorModel
    
    def get_factor_entity(self):
        return PortfolioCompanyShareOptionFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[PortfolioCompanyShareOptionFactorModel]) -> Optional[PortfolioCompanyShareOptionFactor]:
        """Convert ORM model to PortfolioCompanyShareOptionFactor domain entity."""
        if not orm_model:
            return None
        
        return PortfolioCompanyShareOptionFactor(
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
    def to_orm(cls, domain_entity: PortfolioCompanyShareOptionFactor):
        """Convert PortfolioCompanyShareOptionFactor domain entity to ORM model."""
        return PortfolioCompanyShareOptionFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )