"""
src/infrastructure/repositories/mappers/universe/universe_mapper.py

Mappers between the universe domain (Universe, InvestmentUniverse, UniverseFinancialAsset, UniverseFactor) and the
ORM models. ``UniverseMapper.to_domain`` returns the entity of the row's own type (an InvestmentUniverseModel row
gives an InvestmentUniverse) with its members.
"""

from typing import Optional

from src.domain.entities.universe.investment_universe import InvestmentUniverse
from src.domain.entities.universe.universe import Universe
from src.domain.entities.universe.universe_factor import UniverseFactor
from src.domain.entities.universe.universe_financial_asset import UniverseFinancialAsset
from src.infrastructure.models.universe.universe import InvestmentUniverseModel, UniverseModel
from src.infrastructure.models.universe.universe_factor import UniverseFactorModel
from src.infrastructure.models.universe.universe_financial_asset import UniverseFinancialAssetModel


class UniverseFinancialAssetMapper:

    @staticmethod
    def to_domain(orm: Optional[UniverseFinancialAssetModel]) -> Optional[UniverseFinancialAsset]:
        if orm is None:
            return None
        return UniverseFinancialAsset(id=orm.id, universe_id=orm.universe_id, financial_asset_id=orm.financial_asset_id,
                                      start_date=orm.start_date, end_date=orm.end_date)

    @staticmethod
    def to_orm(entity: UniverseFinancialAsset) -> UniverseFinancialAssetModel:
        return UniverseFinancialAssetModel(id=entity.id, universe_id=entity.universe_id,
                                           financial_asset_id=entity.financial_asset_id,
                                           start_date=entity.start_date, end_date=entity.end_date)


class UniverseFactorMapper:

    @staticmethod
    def to_domain(orm: Optional[UniverseFactorModel]) -> Optional[UniverseFactor]:
        if orm is None:
            return None
        return UniverseFactor(id=orm.id, universe_id=orm.universe_id, factor_id=orm.factor_id)

    @staticmethod
    def to_orm(entity: UniverseFactor) -> UniverseFactorModel:
        return UniverseFactorModel(id=entity.id, universe_id=entity.universe_id, factor_id=entity.factor_id)


class UniverseMapper:
    """Any universe row -> the entity of its type, with its members."""

    def to_domain(self, orm: Optional[UniverseModel]) -> Optional[Universe]:
        if orm is None:
            return None
        members = dict(
            financial_assets=[UniverseFinancialAssetMapper.to_domain(m) for m in orm.financial_assets],
            factors=[UniverseFactorMapper.to_domain(m) for m in orm.factors],
        )
        common = dict(id=orm.id, name=orm.name, description=orm.description, version=orm.version or 1,
                      created_at=orm.created_at, updated_at=orm.updated_at)
        if isinstance(orm, InvestmentUniverseModel):
            return InvestmentUniverse(entity_type=orm.entity_type, currency_id=orm.currency_id, **common, **members)
        return Universe(universe_type=orm.universe_type, **common, **members)

    def to_orm(self, entity: Universe) -> UniverseModel:
        orm = (InvestmentUniverseModel() if isinstance(entity, InvestmentUniverse) or hasattr(entity, "entity_type")
               else UniverseModel(universe_type=entity.universe_type or "Universe"))
        orm.id = entity.id
        return self.copy_to_orm(entity, orm)

    def copy_to_orm(self, entity: Universe, orm: UniverseModel) -> UniverseModel:
        """Scalar fields only; members are synchronised by the repository."""
        orm.name = entity.name
        orm.description = entity.description
        orm.version = getattr(entity, "version", 1) or 1
        orm.created_at = entity.created_at
        orm.updated_at = entity.updated_at
        if isinstance(orm, InvestmentUniverseModel):
            orm.entity_type = getattr(entity, "entity_type", None)
            orm.currency_id = getattr(entity, "currency_id", None)
        return orm

    @property
    def model_class(self):
        return UniverseModel


class InvestmentUniverseMapper(UniverseMapper):

    @property
    def model_class(self):
        return InvestmentUniverseModel

    def to_orm(self, entity: Universe) -> InvestmentUniverseModel:
        orm = InvestmentUniverseModel()
        orm.id = entity.id
        return self.copy_to_orm(entity, orm)
