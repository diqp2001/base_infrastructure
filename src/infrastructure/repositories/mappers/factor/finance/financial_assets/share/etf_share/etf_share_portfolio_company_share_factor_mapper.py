"""
Mapper for ETFSharePortfolioCompanyShareFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import ETFSharePortfolioCompanyShareFactorModel
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share_portfolio_company_share_factor import ETFSharePortfolioCompanyShareFactor
from .....base_factor_mapper import BaseFactorMapper


class ETFSharePortfolioCompanyShareFactorMapper(BaseFactorMapper):
    """Mapper for ETFSharePortfolioCompanyShareFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'etf_share_portfolio_company_share'
    
    @property
    def model_class(self):
        return ETFSharePortfolioCompanyShareFactorModel
    
    def get_factor_model(self):
        return ETFSharePortfolioCompanyShareFactorModel
    
    def get_factor_entity(self):
        return ETFSharePortfolioCompanyShareFactor
    
    def to_domain(self, orm_model: Optional[ETFSharePortfolioCompanyShareFactorModel]) -> Optional[ETFSharePortfolioCompanyShareFactor]:
        """Convert ORM model to ETFSharePortfolioCompanyShareFactor domain entity."""
        if not orm_model:
            return None
        
        return ETFSharePortfolioCompanyShareFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition
        )
    
    def to_orm(self, domain_entity: ETFSharePortfolioCompanyShareFactor) -> ETFSharePortfolioCompanyShareFactorModel:
        """Convert ETFSharePortfolioCompanyShareFactor domain entity to ORM model."""
        return ETFSharePortfolioCompanyShareFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )