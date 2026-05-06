"""
Mapper for CompanySharePortfolioOptionDupireLocalVolatilityPriceFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import CompanySharePortfolioOptionDupireLocalVolatilityPriceFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_dupire_local_volatility_price_factor import CompanySharePortfolioOptionDupireLocalVolatilityPriceFactor
from ......base_factor_mapper import BaseFactorMapper


class CompanySharePortfolioOptionDupireLocalVolatilityPriceFactorMapper(BaseFactorMapper):
    """Mapper for CompanySharePortfolioOptionDupireLocalVolatilityPriceFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'company_share_portfolio_option'
    
    @property
    def model_class(self):
        return CompanySharePortfolioOptionDupireLocalVolatilityPriceFactorModel
    
    def get_factor_model(self):
        return CompanySharePortfolioOptionDupireLocalVolatilityPriceFactorModel
    
    def get_factor_entity(self):
        return CompanySharePortfolioOptionDupireLocalVolatilityPriceFactor
    
    def to_domain(self, orm_model: Optional[CompanySharePortfolioOptionDupireLocalVolatilityPriceFactorModel]) -> Optional[CompanySharePortfolioOptionDupireLocalVolatilityPriceFactor]:
        """Convert ORM model to CompanySharePortfolioOptionDupireLocalVolatilityPriceFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanySharePortfolioOptionDupireLocalVolatilityPriceFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    def to_orm(self, domain_entity: CompanySharePortfolioOptionDupireLocalVolatilityPriceFactor) -> CompanySharePortfolioOptionDupireLocalVolatilityPriceFactorModel:
        """Convert CompanySharePortfolioOptionDupireLocalVolatilityPriceFactor domain entity to ORM model."""
        return CompanySharePortfolioOptionDupireLocalVolatilityPriceFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )