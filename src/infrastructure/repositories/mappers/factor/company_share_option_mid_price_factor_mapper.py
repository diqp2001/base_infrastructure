"""
src/infrastructure/repositories/mappers/factor/company_share_option_mid_price_factor_mapper.py

Mapper for CompanyShareOptionMidPriceFactor domain entity to ORM model.
"""

from typing import Optional
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_mid_price_factor import CompanyShareOptionMidPriceFactor
from src.infrastructure.models.factor.factor import CompanyShareOptionMidPriceFactorModel


class CompanyShareOptionMidPriceFactorMapper:
    """Mapper between CompanyShareOptionMidPriceFactor domain entity and ORM model."""

    @property
    def discriminator(self):
        return "company_share_option_mid_price_factor"

    @property
    def model_class(self):
        return CompanyShareOptionMidPriceFactorModel

    def get_entity(self):
        return CompanyShareOptionMidPriceFactor

    def to_domain(self, orm_model: Optional[CompanyShareOptionMidPriceFactorModel]) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None

        return CompanyShareOptionMidPriceFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, entity: CompanyShareOptionMidPriceFactor) -> CompanyShareOptionMidPriceFactorModel:
        """Convert domain entity to ORM model."""
        return CompanyShareOptionMidPriceFactorModel(
            id=entity.id,
            name=entity.name,
            group=entity.group,
            subgroup=entity.subgroup,
            frequency=entity.frequency,
            data_type=entity.data_type,
            source=entity.source,
            definition=entity.definition,
            factor_type=self.discriminator,
        )