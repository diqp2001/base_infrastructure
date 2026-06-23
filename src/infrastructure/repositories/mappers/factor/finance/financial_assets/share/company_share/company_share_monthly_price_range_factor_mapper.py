from typing import Optional
from src.infrastructure.models.factor.factor import CompanyShareMonthlyPriceRangeFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_monthly_price_range_factor import CompanyShareMonthlyPriceRangeFactor


class CompanyShareMonthlyPriceRangeFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self):
        return 'CompanyShare'

    @property
    def model_class(self):
        return CompanyShareMonthlyPriceRangeFactorModel

    def get_factor_model(self):
        return CompanyShareMonthlyPriceRangeFactorModel

    def get_factor_entity(self):
        return CompanyShareMonthlyPriceRangeFactor

    def to_domain(self, orm_model: Optional[CompanyShareMonthlyPriceRangeFactorModel]) -> Optional[CompanyShareMonthlyPriceRangeFactor]:
        if not orm_model:
            return None
        return CompanyShareMonthlyPriceRangeFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, domain_entity: CompanyShareMonthlyPriceRangeFactor) -> CompanyShareMonthlyPriceRangeFactorModel:
        return CompanyShareMonthlyPriceRangeFactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
