from typing import Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_spatio_temporal_feature_factor import (
    CompanyShareSpatioTemporalFeatureFactor,
)
from src.infrastructure.models.factor.company_share_technical_momentum_factor_models import (
    CompanyShareSpatioTemporalFeatureFactorModel,
)
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CompanyShareSpatioTemporalFeatureFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self):
        return 'CompanyShare'

    @property
    def model_class(self):
        return CompanyShareSpatioTemporalFeatureFactorModel

    def get_factor_model(self):
        return CompanyShareSpatioTemporalFeatureFactorModel

    def get_factor_entity(self):
        return CompanyShareSpatioTemporalFeatureFactor

    def to_domain(
        self, orm_model: Optional[CompanyShareSpatioTemporalFeatureFactorModel]
    ) -> Optional[CompanyShareSpatioTemporalFeatureFactor]:
        if not orm_model:
            return None
        return CompanyShareSpatioTemporalFeatureFactor(
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
        self, domain_entity: CompanyShareSpatioTemporalFeatureFactor
    ) -> CompanyShareSpatioTemporalFeatureFactorModel:
        return CompanyShareSpatioTemporalFeatureFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type='company_share_spatio_temporal_feature_factor',
        )
