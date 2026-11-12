"""
CompanyShareFundamentalValuationFactor Mapper - a calculated company fundamental factor (its name carries the measure).
"""

from typing import Optional
from src.infrastructure.models.factor.factor import CompanyShareFundamentalValuationFactorModel
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_valuation_factor import CompanyShareFundamentalValuationFactor
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CompanyShareFundamentalValuationFactorMapper(BaseFactorMapper):
    """Mapper for CompanyShareFundamentalValuationFactor domain entity and ORM model conversion."""
    @property
    def discriminator(self):
        return 'CompanyShareFundamentalValuation'

    def get_factor_model(self):
        return CompanyShareFundamentalValuationFactorModel

    def get_factor_entity(self):
        return CompanyShareFundamentalValuationFactor

    @property
    def model_class(self):
        return CompanyShareFundamentalValuationFactorModel

    @staticmethod
    def to_domain(orm_model: Optional[CompanyShareFundamentalValuationFactorModel]) -> Optional[CompanyShareFundamentalValuationFactor]:
        """Convert ORM model to CompanyShareFundamentalValuationFactor domain entity."""
        if not orm_model:
            return None
        return CompanyShareFundamentalValuationFactor(
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
    def to_orm(domain_entity: CompanyShareFundamentalValuationFactor) -> CompanyShareFundamentalValuationFactorModel:
        """Convert CompanyShareFundamentalValuationFactor domain entity to ORM model."""
        return CompanyShareFundamentalValuationFactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
