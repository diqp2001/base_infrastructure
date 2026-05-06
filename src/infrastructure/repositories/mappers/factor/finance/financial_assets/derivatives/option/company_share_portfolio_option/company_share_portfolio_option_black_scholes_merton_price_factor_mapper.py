"""
Mapper for CompanySharePortfolioOptionBlackScholesMertonPriceFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import CompanySharePortfolioOptionBlackScholesMertonPriceFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_black_scholes_merton_price_factor import CompanySharePortfolioOptionBlackScholesMertonPriceFactor
from ......base_factor_mapper import BaseFactorMapper


class CompanySharePortfolioOptionBlackScholesMertonPriceFactorMapper(BaseFactorMapper):
    """Mapper for CompanySharePortfolioOptionBlackScholesMertonPriceFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'company_share_portfolio_option'
    
    @property
    def model_class(self):
        return CompanySharePortfolioOptionBlackScholesMertonPriceFactorModel
    
    def get_factor_model(self):
        return CompanySharePortfolioOptionBlackScholesMertonPriceFactorModel
    
    def get_factor_entity(self):
        return CompanySharePortfolioOptionBlackScholesMertonPriceFactor
    
    def to_domain(self, orm_model: Optional[CompanySharePortfolioOptionBlackScholesMertonPriceFactorModel]) -> Optional[CompanySharePortfolioOptionBlackScholesMertonPriceFactor]:
        """Convert ORM model to CompanySharePortfolioOptionBlackScholesMertonPriceFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanySharePortfolioOptionBlackScholesMertonPriceFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    def to_orm(self, domain_entity: CompanySharePortfolioOptionBlackScholesMertonPriceFactor) -> CompanySharePortfolioOptionBlackScholesMertonPriceFactorModel:
        """Convert CompanySharePortfolioOptionBlackScholesMertonPriceFactor domain entity to ORM model."""
        return CompanySharePortfolioOptionBlackScholesMertonPriceFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )