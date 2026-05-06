"""
src/infrastructure/repositories/mappers/factor/company_share_mid_price_factor_mapper.py

Mapper for CompanyShareMidPriceFactor domain entity to ORM model.
"""

from typing import Optional
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_mid_price_factor import CompanyShareMidPriceFactor
from src.infrastructure.models.factor.factor import CompanyShareMidPriceFactorModel


class CompanyShareMidPriceFactorMapper:
    """Mapper between CompanyShareMidPriceFactor domain entity and ORM model."""

    @property
    def discriminator(self):
        return "company_share_mid_price_factor"

    @property
    def model_class(self):
        return CompanyShareMidPriceFactorModel

    def get_entity(self):
        return CompanyShareMidPriceFactor

    def to_domain(self, orm_model: Optional[CompanyShareMidPriceFactorModel]) -> Optional[CompanyShareMidPriceFactor]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None

        return CompanyShareMidPriceFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, entity: CompanyShareMidPriceFactor) -> CompanyShareMidPriceFactorModel:
        """Convert domain entity to ORM model."""
        return CompanyShareMidPriceFactorModel(
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