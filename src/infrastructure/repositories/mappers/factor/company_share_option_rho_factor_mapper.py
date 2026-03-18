"""
Mapper for CompanyShareOptionRhoFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import CompanyShareOptionRhoFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rho_factor import CompanyShareOptionRhoFactor
from .base_factor_mapper import BaseFactorMapper


class CompanyShareOptionRhoFactorMapper(BaseFactorMapper):
    """Mapper for CompanyShareOptionRhoFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'company_share_option_rho_factor'
    
    @property
    def model_class(self):
        return CompanyShareOptionRhoFactorModel
    
    def get_factor_model(self):
        return CompanyShareOptionRhoFactorModel
    
    def get_factor_entity(self):
        return CompanyShareOptionRhoFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[CompanyShareOptionRhoFactorModel]) -> Optional[CompanyShareOptionRhoFactor]:
        """Convert ORM model to CompanyShareOptionRhoFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanyShareOptionRhoFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
            stock_price=getattr(orm_model, 'stock_price', None),
            strike_price=getattr(orm_model, 'strike_price', None),
            volatility=getattr(orm_model, 'volatility', None),
            time_to_expiry=getattr(orm_model, 'time_to_expiry', None),
            underlying_symbol=getattr(orm_model, 'underlying_symbol', None)
        )
    
    @classmethod
    def to_orm(cls, domain_entity: CompanyShareOptionRhoFactor):
        """Convert CompanyShareOptionRhoFactor domain entity to ORM model."""
        return CompanyShareOptionRhoFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )