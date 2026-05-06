"""
Mapper for ETFSharePortfolioCompanySharePriceReturnFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import ETFSharePortfolioCompanySharePriceReturnFactorModel
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share_portfolio_company_share_price_return_factor import ETFSharePortfolioCompanySharePriceReturnFactor
from .....base_factor_mapper import BaseFactorMapper


class ETFSharePortfolioCompanySharePriceReturnFactorMapper(BaseFactorMapper):
    """Mapper for ETFSharePortfolioCompanySharePriceReturnFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'etf_share_portfolio_company_share'
    
    @property
    def model_class(self):
        return ETFSharePortfolioCompanySharePriceReturnFactorModel
    
    def get_factor_model(self):
        return ETFSharePortfolioCompanySharePriceReturnFactorModel
    
    def get_factor_entity(self):
        return ETFSharePortfolioCompanySharePriceReturnFactor
    
    def to_domain(self, orm_model: Optional[ETFSharePortfolioCompanySharePriceReturnFactorModel]) -> Optional[ETFSharePortfolioCompanySharePriceReturnFactor]:
        """Convert ORM model to ETFSharePortfolioCompanySharePriceReturnFactor domain entity."""
        if not orm_model:
            return None
        
        return ETFSharePortfolioCompanySharePriceReturnFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition
        )
    
    def to_orm(self, domain_entity: ETFSharePortfolioCompanySharePriceReturnFactor) -> ETFSharePortfolioCompanySharePriceReturnFactorModel:
        """Convert ETFSharePortfolioCompanySharePriceReturnFactor domain entity to ORM model."""
        return ETFSharePortfolioCompanySharePriceReturnFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )