"""
Mapper for ETFSharePortfolioCompanyShareOptionDeltaFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import ETFSharePortfolioCompanyShareOptionDeltaFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_portfolio_company_share_option.etf_share_portfolio_company_share_option_delta_factor import ETFSharePortfolioCompanyShareOptionDeltaFactor
from .base_factor_mapper import BaseFactorMapper


class ETFSharePortfolioCompanyShareOptionDeltaFactorMapper(BaseFactorMapper):
    """Mapper for ETFSharePortfolioCompanyShareOptionDeltaFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'etf_share_portfolio_company_share_option'
    
    @property
    def model_class(self):
        return ETFSharePortfolioCompanyShareOptionDeltaFactorModel
    
    def get_factor_model(self):
        return ETFSharePortfolioCompanyShareOptionDeltaFactorModel
    
    def get_factor_entity(self):
        return ETFSharePortfolioCompanyShareOptionDeltaFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[ETFSharePortfolioCompanyShareOptionDeltaFactorModel]) -> Optional[ETFSharePortfolioCompanyShareOptionDeltaFactor]:
        """Convert ORM model to ETFSharePortfolioCompanyShareOptionDeltaFactor domain entity."""
        if not orm_model:
            return None
        
        return ETFSharePortfolioCompanyShareOptionDeltaFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    @classmethod
    def to_orm(cls, domain_entity: ETFSharePortfolioCompanyShareOptionDeltaFactor):
        """Convert ETFSharePortfolioCompanyShareOptionDeltaFactor domain entity to ORM model."""
        return ETFSharePortfolioCompanyShareOptionDeltaFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )