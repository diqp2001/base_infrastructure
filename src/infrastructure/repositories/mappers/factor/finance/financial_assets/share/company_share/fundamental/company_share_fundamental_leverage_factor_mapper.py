"""
CompanyShareFundamentalLeverageFactor Mapper - a calculated company fundamental factor (its name carries the measure).
"""

from typing import Optional
from src.infrastructure.models.factor.factor import CompanyShareFundamentalLeverageFactorModel
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_leverage_factor import CompanyShareFundamentalLeverageFactor
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CompanyShareFundamentalLeverageFactorMapper(BaseFactorMapper):
    """Mapper for CompanyShareFundamentalLeverageFactor domain entity and ORM model conversion."""
    @property
    def discriminator(self):
        return 'CompanyShareFundamentalLeverage'

    def get_factor_model(self):
        return CompanyShareFundamentalLeverageFactorModel

    def get_factor_entity(self):
        return CompanyShareFundamentalLeverageFactor

    @property
    def model_class(self):
        return CompanyShareFundamentalLeverageFactorModel

    @staticmethod
    def to_domain(orm_model: Optional[CompanyShareFundamentalLeverageFactorModel]) -> Optional[CompanyShareFundamentalLeverageFactor]:
        """Convert ORM model to CompanyShareFundamentalLeverageFactor domain entity."""
        if not orm_model:
            return None
        return CompanyShareFundamentalLeverageFactor(
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
    def to_orm(domain_entity: CompanyShareFundamentalLeverageFactor) -> CompanyShareFundamentalLeverageFactorModel:
        """Convert CompanyShareFundamentalLeverageFactor domain entity to ORM model."""
        return CompanyShareFundamentalLeverageFactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
