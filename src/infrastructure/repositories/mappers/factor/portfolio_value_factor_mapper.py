"""
Portfolio Value Factor Mapper

Maps between PortfolioValueFactor domain entities and PortfolioValueFactorModel ORM models.
"""

from typing import Optional

from src.domain.entities.factor.finance.portfolio.portfolio_value_factor import PortfolioValueFactor
from src.infrastructure.models.factor.factor import PortfolioValueFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class PortfolioValueFactorMapper(BaseFactorMapper):
    """Mapper for PortfolioValueFactor domain entity."""

    @property
    def discriminator(self):
        return 'portfolio'

    @property
    def model_class(self):
        return PortfolioValueFactorModel
    
    def get_factor_model(self):
        return PortfolioValueFactorModel
    
    def get_factor_entity(self):
        return PortfolioValueFactor
    
    def to_domain(self, orm_model: Optional[PortfolioValueFactorModel]) -> Optional[PortfolioValueFactor]:
        """Convert ORM model to PortfolioValueFactor domain entity."""
        if not orm_model:
            return None
        
        return PortfolioValueFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition
        )
    
    def to_orm(self, domain_entity: PortfolioValueFactor) -> PortfolioValueFactorModel:
        """Convert PortfolioValueFactor domain entity to ORM model."""
        return PortfolioValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type="portfolio_value_factor"
        )