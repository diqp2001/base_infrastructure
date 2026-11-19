"""
src/infrastructure/repositories/local_repo/universe/universe_membership_repositories.py

Row-level repositories of the two universe member types. They apply the same rule as the Universe entity before
inserting (DuplicateMembership: same factor, or an overlapping window of the same financial asset) - the unique
constraints are the last line of defence (a NULL start_date compares differently across databases).
Raise on failure (after rolling back).
"""

from datetime import date
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.domain.entities.universe.universe import DuplicateMembership
from src.domain.entities.universe.universe_factor import UniverseFactor
from src.domain.entities.universe.universe_financial_asset import UniverseFinancialAsset
from src.domain.ports.universe.universe_port import UniverseFactorPort, UniverseFinancialAssetPort
from src.infrastructure.models.universe.universe_factor import UniverseFactorModel
from src.infrastructure.models.universe.universe_financial_asset import UniverseFinancialAssetModel
from src.infrastructure.repositories.mappers.universe.universe_mapper import (
    UniverseFactorMapper,
    UniverseFinancialAssetMapper,
)


class _MemberBase:
    model_class = None
    mapper = None

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory

    def _insert(self, entity):
        try:
            orm = self.mapper.to_orm(entity)
            self.session.add(orm)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        entity.id = orm.id
        return entity

    def get_by_id(self, id: int):
        return self.mapper.to_domain(self.session.query(self.model_class)
                                     .filter(self.model_class.id == id).one_or_none())

    def delete(self, id: int) -> bool:
        row = self.session.query(self.model_class).filter(self.model_class.id == id).one_or_none()
        if row is None:
            return False
        try:
            self.session.delete(row)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return True


class UniverseFinancialAssetRepository(_MemberBase, UniverseFinancialAssetPort):
    model_class = UniverseFinancialAssetModel
    mapper = UniverseFinancialAssetMapper

    def get_by_universe(self, universe_id: int, on: Optional[date] = None) -> List[UniverseFinancialAsset]:
        query = self.session.query(UniverseFinancialAssetModel).filter(
            UniverseFinancialAssetModel.universe_id == universe_id)
        if on is not None:
            query = query.filter(
                or_(UniverseFinancialAssetModel.start_date.is_(None), UniverseFinancialAssetModel.start_date <= on),
                or_(UniverseFinancialAssetModel.end_date.is_(None), UniverseFinancialAssetModel.end_date > on))
        return [self.mapper.to_domain(r) for r in query.order_by(UniverseFinancialAssetModel.id).all()]

    def get_by_financial_asset(self, financial_asset_id: int) -> List[UniverseFinancialAsset]:
        rows = (self.session.query(UniverseFinancialAssetModel)
                .filter(UniverseFinancialAssetModel.financial_asset_id == financial_asset_id)
                .order_by(UniverseFinancialAssetModel.id).all())
        return [self.mapper.to_domain(r) for r in rows]

    def add(self, entity: UniverseFinancialAsset) -> UniverseFinancialAsset:
        if entity.universe_id is None:
            raise ValueError("a universe financial asset needs a universe_id")
        for existing in self.get_by_universe(entity.universe_id):
            if (existing.financial_asset_id == entity.financial_asset_id
                    and existing.overlaps(entity.start_date, entity.end_date)):
                raise DuplicateMembership(f"financial asset {entity.financial_asset_id} is already a member of "
                                          f"universe {entity.universe_id}")
        return self._insert(entity)


class UniverseFactorRepository(_MemberBase, UniverseFactorPort):
    model_class = UniverseFactorModel
    mapper = UniverseFactorMapper

    def get_by_universe(self, universe_id: int) -> List[UniverseFactor]:
        rows = (self.session.query(UniverseFactorModel).filter(UniverseFactorModel.universe_id == universe_id)
                .order_by(UniverseFactorModel.id).all())
        return [self.mapper.to_domain(r) for r in rows]

    def add(self, entity: UniverseFactor) -> UniverseFactor:
        if entity.universe_id is None:
            raise ValueError("a universe factor needs a universe_id")
        duplicate = (self.session.query(UniverseFactorModel.id)
                     .filter(UniverseFactorModel.universe_id == entity.universe_id,
                             UniverseFactorModel.factor_id == entity.factor_id).first())
        if duplicate:
            raise DuplicateMembership(f"factor {entity.factor_id} is already a member of universe {entity.universe_id}")
        return self._insert(entity)
