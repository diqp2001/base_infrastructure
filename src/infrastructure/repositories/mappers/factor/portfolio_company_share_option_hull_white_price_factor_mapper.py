"""
Mapper for PortfolioCompanyShareOptionHullWhitePriceFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import PortfolioCompanyShareOptionHullWhitePriceFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_hull_white_price_factor import PortfolioCompanyShareOptionHullWhitePriceFactor
from .base_factor_mapper import BaseFactorMapper


class PortfolioCompanyShareOptionHullWhitePriceFactorMapper(BaseFactorMapper):
    """Mapper for PortfolioCompanyShareOptionHullWhitePriceFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'portfolio_company_share_option'
    
    @property
    def model_class(self):
        return PortfolioCompanyShareOptionHullWhitePriceFactorModel
    
    def get_factor_model(self):
        return PortfolioCompanyShareOptionHullWhitePriceFactorModel
    
    def get_factor_entity(self):
        return PortfolioCompanyShareOptionHullWhitePriceFactor
    
    def to_domain(self, orm_model: Optional[PortfolioCompanyShareOptionHullWhitePriceFactorModel]) -> Optional[PortfolioCompanyShareOptionHullWhitePriceFactor]:
        """Convert ORM model to PortfolioCompanyShareOptionHullWhitePriceFactor domain entity."""
        if not orm_model:
            return None
        
        return PortfolioCompanyShareOptionHullWhitePriceFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    def to_orm(self, domain_entity: PortfolioCompanyShareOptionHullWhitePriceFactor) -> PortfolioCompanyShareOptionHullWhitePriceFactorModel:
        """Convert PortfolioCompanyShareOptionHullWhitePriceFactor domain entity to ORM model."""
        return PortfolioCompanyShareOptionHullWhitePriceFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )