"""
CompanyShareFundamentalStatementItemFactor Mapper - a calculated company fundamental factor (its name carries the measure).
"""

from typing import Optional
from src.infrastructure.models.factor.factor import CompanyShareFundamentalStatementItemFactorModel
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_statement_item_factor import CompanyShareFundamentalStatementItemFactor
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CompanyShareFundamentalStatementItemFactorMapper(BaseFactorMapper):
    """Mapper for CompanyShareFundamentalStatementItemFactor domain entity and ORM model conversion."""
    @property
    def discriminator(self):
        return 'CompanyShareFundamentalStatementItem'

    def get_factor_model(self):
        return CompanyShareFundamentalStatementItemFactorModel

    def get_factor_entity(self):
        return CompanyShareFundamentalStatementItemFactor

    @property
    def model_class(self):
        return CompanyShareFundamentalStatementItemFactorModel

    @staticmethod
    def to_domain(orm_model: Optional[CompanyShareFundamentalStatementItemFactorModel]) -> Optional[CompanyShareFundamentalStatementItemFactor]:
        """Convert ORM model to CompanyShareFundamentalStatementItemFactor domain entity."""
        if not orm_model:
            return None
        return CompanyShareFundamentalStatementItemFactor(
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
    def to_orm(domain_entity: CompanyShareFundamentalStatementItemFactor) -> CompanyShareFundamentalStatementItemFactorModel:
        """Convert CompanyShareFundamentalStatementItemFactor domain entity to ORM model."""
        return CompanyShareFundamentalStatementItemFactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
