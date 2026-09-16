from typing import Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_lgbm_cs_quintile_rank_momentum_factor import (
    CompanyShareLGBMCSQuintileRankMomentumFactor,
)
from src.infrastructure.models.factor.company_share_technical_momentum_factor_models import (
    CompanyShareLGBMCSQuintileRankMomentumFactorModel,
)
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CompanyShareLGBMCSQuintileRankMomentumFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self):
        return 'CompanyShare'

    @property
    def model_class(self):
        return CompanyShareLGBMCSQuintileRankMomentumFactorModel

    def get_factor_model(self):
        return CompanyShareLGBMCSQuintileRankMomentumFactorModel

    def get_factor_entity(self):
        return CompanyShareLGBMCSQuintileRankMomentumFactor

    def to_domain(
        self, orm_model: Optional[CompanyShareLGBMCSQuintileRankMomentumFactorModel]
    ) -> Optional[CompanyShareLGBMCSQuintileRankMomentumFactor]:
        if not orm_model:
            return None
        return CompanyShareLGBMCSQuintileRankMomentumFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(
        self, domain_entity: CompanyShareLGBMCSQuintileRankMomentumFactor
    ) -> CompanyShareLGBMCSQuintileRankMomentumFactorModel:
        return CompanyShareLGBMCSQuintileRankMomentumFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type='company_share_lgbm_cs_quintile_rank_momentum_factor',
        )
