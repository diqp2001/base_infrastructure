"""
Portfolio Holding Value Factor Mapper

Maps between PortfolioHoldingValueFactor domain entities and PortfolioHoldingValueFactorModel ORM models.
"""

from typing import Optional

from src.domain.entities.factor.finance.holding.portfolio_holding_value_factor import PortfolioHoldingValueFactor
from src.infrastructure.models.factor.factor import PortfolioHoldingValueFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class PortfolioHoldingValueFactorMapper(BaseFactorMapper):
    """Mapper for PortfolioHoldingValueFactor domain entity."""

    @property
    def discriminator(self):
        return 'PortfolioHolding'

    @property
    def model_class(self):
        return PortfolioHoldingValueFactorModel
    
    def get_factor_model(self):
        return PortfolioHoldingValueFactorModel
    
    def get_factor_entity(self):
        return PortfolioHoldingValueFactor
    
    def to_domain(self, orm_model: Optional[PortfolioHoldingValueFactorModel]) -> Optional[PortfolioHoldingValueFactor]:
        """Convert ORM model to PortfolioHoldingValueFactor domain entity."""
        if not orm_model:
            return None
        
        return PortfolioHoldingValueFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition
        )
    
    def to_orm(self, domain_entity: PortfolioHoldingValueFactor) -> PortfolioHoldingValueFactorModel:
        """Convert PortfolioHoldingValueFactor domain entity to ORM model."""
        return PortfolioHoldingValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type="portfolio_holding_value_factor"
        )