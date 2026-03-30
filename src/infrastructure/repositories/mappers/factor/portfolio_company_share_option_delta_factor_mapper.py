"""
Mapper for PortfolioCompanyShareOptionDeltaFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import PortfolioCompanyShareOptionDeltaFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_delta_factor import PortfolioCompanyShareOptionDeltaFactor
from .base_factor_mapper import BaseFactorMapper


class PortfolioCompanyShareOptionDeltaFactorMapper(BaseFactorMapper):
    """Mapper for PortfolioCompanyShareOptionDeltaFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'portfolio_company_share_option'
    
    @property
    def model_class(self):
        return PortfolioCompanyShareOptionDeltaFactorModel
    
    def get_factor_model(self):
        return PortfolioCompanyShareOptionDeltaFactorModel
    
    def get_factor_entity(self):
        return PortfolioCompanyShareOptionDeltaFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[PortfolioCompanyShareOptionDeltaFactorModel]) -> Optional[PortfolioCompanyShareOptionDeltaFactor]:
        """Convert ORM model to PortfolioCompanyShareOptionDeltaFactor domain entity."""
        if not orm_model:
            return None
        
        return PortfolioCompanyShareOptionDeltaFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    @classmethod
    def to_orm(cls, domain_entity: PortfolioCompanyShareOptionDeltaFactor):
        """Convert PortfolioCompanyShareOptionDeltaFactor domain entity to ORM model."""
        return PortfolioCompanyShareOptionDeltaFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )