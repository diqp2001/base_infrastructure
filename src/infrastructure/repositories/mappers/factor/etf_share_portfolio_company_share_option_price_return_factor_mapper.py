"""
Mapper for ETFSharePortfolioCompanyShareOptionPriceReturnFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import ETFSharePortfolioCompanyShareOptionPriceReturnFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_portfolio_company_share_option.etf_share_portfolio_company_share_option_price_return_factor import ETFSharePortfolioCompanyShareOptionPriceReturnFactor
from .base_factor_mapper import BaseFactorMapper


class ETFSharePortfolioCompanyShareOptionPriceReturnFactorMapper(BaseFactorMapper):
    """Mapper for ETFSharePortfolioCompanyShareOptionPriceReturnFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'etf_share_portfolio_company_share_option'
    
    @property
    def model_class(self):
        return ETFSharePortfolioCompanyShareOptionPriceReturnFactorModel
    
    def get_factor_model(self):
        return ETFSharePortfolioCompanyShareOptionPriceReturnFactorModel
    
    def get_factor_entity(self):
        return ETFSharePortfolioCompanyShareOptionPriceReturnFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[ETFSharePortfolioCompanyShareOptionPriceReturnFactorModel]) -> Optional[ETFSharePortfolioCompanyShareOptionPriceReturnFactor]:
        """Convert ORM model to ETFSharePortfolioCompanyShareOptionPriceReturnFactor domain entity."""
        if not orm_model:
            return None
        
        return ETFSharePortfolioCompanyShareOptionPriceReturnFactor(
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
    def to_orm(cls, domain_entity: ETFSharePortfolioCompanyShareOptionPriceReturnFactor):
        """Convert ETFSharePortfolioCompanyShareOptionPriceReturnFactor domain entity to ORM model."""
        return ETFSharePortfolioCompanyShareOptionPriceReturnFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )