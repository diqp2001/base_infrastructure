"""
CompanyShareFundamentalProfitabilityFactor Mapper - a calculated company fundamental factor (its name carries the measure).
"""

from typing import Optional
from src.infrastructure.models.factor.factor import CompanyShareFundamentalProfitabilityFactorModel
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_profitability_factor import CompanyShareFundamentalProfitabilityFactor
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CompanyShareFundamentalProfitabilityFactorMapper(BaseFactorMapper):
    """Mapper for CompanyShareFundamentalProfitabilityFactor domain entity and ORM model conversion."""
    @property
    def discriminator(self):
        return 'CompanyShareFundamentalProfitability'

    def get_factor_model(self):
        return CompanyShareFundamentalProfitabilityFactorModel

    def get_factor_entity(self):
        return CompanyShareFundamentalProfitabilityFactor

    @property
    def model_class(self):
        return CompanyShareFundamentalProfitabilityFactorModel

    @staticmethod
    def to_domain(orm_model: Optional[CompanyShareFundamentalProfitabilityFactorModel]) -> Optional[CompanyShareFundamentalProfitabilityFactor]:
        """Convert ORM model to CompanyShareFundamentalProfitabilityFactor domain entity."""
        if not orm_model:
            return None
        return CompanyShareFundamentalProfitabilityFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
        )

    @staticmethod
    def to_orm(domain_entity: CompanyShareFundamentalProfitabilityFactor) -> CompanyShareFundamentalProfitabilityFactorModel:
        """Convert CompanyShareFundamentalProfitabilityFactor domain entity to ORM model."""
        return CompanyShareFundamentalProfitabilityFactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
