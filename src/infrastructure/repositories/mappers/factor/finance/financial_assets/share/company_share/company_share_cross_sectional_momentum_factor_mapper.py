from typing import Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_cross_sectional_momentum_factor import (
    CompanyShareCrossSectionalMomentumFactor,
)
from src.infrastructure.models.factor.company_share_technical_momentum_factor_models import (
    CompanyShareCrossSectionalMomentumFactorModel,
)
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CompanyShareCrossSectionalMomentumFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self):
        return 'CompanyShare'

    @property
    def model_class(self):
        return CompanyShareCrossSectionalMomentumFactorModel

    def get_factor_model(self):
        return CompanyShareCrossSectionalMomentumFactorModel

    def get_factor_entity(self):
        return CompanyShareCrossSectionalMomentumFactor

    def to_domain(
        self, orm_model: Optional[CompanyShareCrossSectionalMomentumFactorModel]
    ) -> Optional[CompanyShareCrossSectionalMomentumFactor]:
        if not orm_model:
            return None
        return CompanyShareCrossSectionalMomentumFactor(
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
        self, domain_entity: CompanyShareCrossSectionalMomentumFactor
    ) -> CompanyShareCrossSectionalMomentumFactorModel:
        return CompanyShareCrossSectionalMomentumFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type='company_share_cross_sectional_momentum_factor',
        )
