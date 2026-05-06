"""
Mapper for PortfolioCompanyShareOptionBlackScholesMertonPriceFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import PortfolioCompanyShareOptionBlackScholesMertonPriceFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_black_scholes_merton_price_factor import PortfolioCompanyShareOptionBlackScholesMertonPriceFactor
from ......base_factor_mapper import BaseFactorMapper


class PortfolioCompanyShareOptionBlackScholesMertonPriceFactorMapper(BaseFactorMapper):
    """Mapper for PortfolioCompanyShareOptionBlackScholesMertonPriceFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'portfolio_company_share_option'
    
    @property
    def model_class(self):
        return PortfolioCompanyShareOptionBlackScholesMertonPriceFactorModel
    
    def get_factor_model(self):
        return PortfolioCompanyShareOptionBlackScholesMertonPriceFactorModel
    
    def get_factor_entity(self):
        return PortfolioCompanyShareOptionBlackScholesMertonPriceFactor
    
    def to_domain(self, orm_model: Optional[PortfolioCompanyShareOptionBlackScholesMertonPriceFactorModel]) -> Optional[PortfolioCompanyShareOptionBlackScholesMertonPriceFactor]:
        """Convert ORM model to PortfolioCompanyShareOptionBlackScholesMertonPriceFactor domain entity."""
        if not orm_model:
            return None
        
        return PortfolioCompanyShareOptionBlackScholesMertonPriceFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    def to_orm(self, domain_entity: PortfolioCompanyShareOptionBlackScholesMertonPriceFactor) -> PortfolioCompanyShareOptionBlackScholesMertonPriceFactorModel:
        """Convert PortfolioCompanyShareOptionBlackScholesMertonPriceFactor domain entity to ORM model."""
        return PortfolioCompanyShareOptionBlackScholesMertonPriceFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )