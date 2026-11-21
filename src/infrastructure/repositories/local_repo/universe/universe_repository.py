"""
src/infrastructure/repositories/local_repo/universe/universe_repository.py

Local SQLAlchemy repository of Universe (any type) and its members (UniverseFinancialAsset, UniverseFactor).

``add`` / ``update`` persist the universe with exactly the members the entity holds (members removed from the entity
are deleted). Membership rules (no duplicate / overlapping membership) are the Universe entity's: ``add_financial_asset``
/ ``add_factor`` load the universe, apply the change through the entity, then save. Unlike the InvestmentUniverse
repository it raises on failure (after rolling back): a universe that was not saved must never look saved.
"""

from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.entities.universe.universe import Universe
from src.domain.entities.universe.universe_factor import UniverseFactor
from src.domain.entities.universe.universe_financial_asset import UniverseFinancialAsset
from src.domain.ports.universe.universe_port import UniversePort
from src.infrastructure.models.universe.universe import UniverseModel
from src.infrastructure.repositories.mappers.universe.universe_mapper import (
    UniverseFactorMapper,
    UniverseFinancialAssetMapper,
    UniverseMapper,
)


# stored asset discriminators -> the domain class names strategies use (compared without case / underscores)
_DOMAIN_TYPES = {"companyshare": "CompanyShare", "companyshareoption": "CompanyShareOption", "etfshare": "ETFShare",
                 "etfshareoption": "ETFShareOption", "future": "Future", "futures": "Future", "index": "Index",
                 "currency": "Currency", "bond": "Bond", "commodity": "Commodity"}


def domain_asset_type(stored: Optional[str]) -> str:
    """'company_share' -> 'CompanyShare', 'futures' -> 'Future'; an unknown name is kept as stored."""
    key = str(stored or "").replace("_", "").lower()
    return _DOMAIN_TYPES.get(key, str(stored or ""))


class UniverseRepository(UniversePort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = UniverseMapper()

    @property
    def model_class(self):
        return UniverseModel

    @property
    def entity_class(self):
        return Universe

    def _to_entity(self, orm) -> Optional[Universe]:
        return self.mapper.to_domain(orm)

    def _to_model(self, entity: Universe) -> UniverseModel:
        return self.mapper.to_orm(entity)

    def _row(self, id: int) -> Optional[UniverseModel]:
        return self.session.query(UniverseModel).filter(UniverseModel.id == id).one_or_none()

    # -- reads ----------------------------------------------------------------------------------------------------
    def get_by_id(self, id: int) -> Optional[Universe]:
        return self._to_entity(self._row(id))

    def get_by_name(self, name: str, version: Optional[int] = None) -> Optional[Universe]:
        """The given version, or the latest one."""
        query = self.session.query(UniverseModel).filter(UniverseModel.name == name)
        if version is not None:
            return self._to_entity(query.filter(UniverseModel.version == version).one_or_none())
        return self._to_entity(query.order_by(UniverseModel.version.desc()).first())

    def get_all(self) -> List[Universe]:
        return [self._to_entity(o) for o in self.session.query(UniverseModel).order_by(UniverseModel.id).all()]

    def get_by_type(self, universe_type: str) -> List[Universe]:
        rows = (self.session.query(UniverseModel).filter(UniverseModel.universe_type == universe_type)
                .order_by(UniverseModel.id).all())
        return [self._to_entity(o) for o in rows]

    def latest_version_number(self, name: str) -> int:
        value = self.session.query(func.max(UniverseModel.version)).filter(UniverseModel.name == name).scalar()
        return int(value or 0)

    # -- writes ---------------------------------------------------------------------------------------------------
    def _commit(self):
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def _sync_members(self, entity: Universe, orm: UniverseModel) -> None:
        """Make the row's members exactly the entity's (matched by id; new members inserted)."""
        keep_assets = {m.id for m in entity.financial_assets if m.id is not None}
        for row in list(orm.financial_assets):
            if row.id not in keep_assets:
                orm.financial_assets.remove(row)
        by_id = {row.id: row for row in orm.financial_assets}
        for member in entity.financial_assets:
            row = by_id.get(member.id)
            if row is None:
                orm.financial_assets.append(UniverseFinancialAssetMapper.to_orm(member))
            else:
                row.financial_asset_id, row.start_date, row.end_date = (
                    member.financial_asset_id, member.start_date, member.end_date)
        keep_factors = {f.id for f in entity.factors if f.id is not None}
        for row in list(orm.factors):
            if row.id not in keep_factors:
                orm.factors.remove(row)
        known = {row.id for row in orm.factors}
        for member in entity.factors:
            if member.id not in known:
                orm.factors.append(UniverseFactorMapper.to_orm(member))

    def _store(self, entity: Universe, orm: UniverseModel) -> Universe:
        try:
            self.mapper.copy_to_orm(entity, orm)
            self._sync_members(entity, orm)
            self.session.add(orm)
            self.session.flush()
        except Exception:
            self.session.rollback()
            raise
        self._commit()
        stored = self._to_entity(orm)
        entity.id = stored.id
        entity.financial_assets, entity.factors = stored.financial_assets, stored.factors
        return entity

    def add(self, entity: Universe) -> Universe:
        now = datetime.utcnow()
        entity.created_at = entity.created_at or now
        entity.updated_at = entity.updated_at or now
        return self._store(entity, self._to_model(entity))

    def update(self, entity: Universe) -> Universe:
        orm = self._row(entity.id) if entity.id is not None else None
        if orm is None:
            raise LookupError(f"universe {entity.id} does not exist")
        entity.updated_at = datetime.utcnow()
        return self._store(entity, orm)

    def delete(self, id: int) -> bool:
        orm = self._row(id)
        if orm is None:
            return False
        self.session.delete(orm)
        self._commit()
        return True

    def _create_or_get(self, entity_cls=None, primary_key: str = None, **kwargs) -> Universe:
        """The universe named ``primary_key`` (latest version), created (version 1) when missing."""
        existing = self.get_by_name(primary_key)
        if existing:
            return existing
        cls = entity_cls if isinstance(entity_cls, type) and issubclass(entity_cls, Universe) else Universe
        fields = {k: kwargs[k] for k in ("description", "universe_type", "version", "entity_type", "currency_id")
                  if k in kwargs}
        return self.add(cls(name=primary_key, **fields))

    def resolve_financial_assets(self, symbols: Iterable[str], asset_type: Optional[str] = None) -> Dict[str, int]:
        """{symbol: financial asset id} of the stored assets with these symbols. ``asset_type`` (a domain class name,
        e.g. 'CompanyShare') keeps the assets of that type (discriminators compared without case / underscores);
        a symbol stored for several assets and no type given resolves to none (ambiguous)."""
        from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
        wanted = sorted({s for s in symbols if s})
        if not wanted:
            return {}

        def norm(value) -> str:
            return str(value or "").replace("_", "").lower()

        found: Dict[str, List[int]] = {}
        for start in range(0, len(wanted), 500):
            rows = (self.session.query(FinancialAssetModel.id, FinancialAssetModel.symbol,
                                       FinancialAssetModel.entity_type)
                    .filter(FinancialAssetModel.symbol.in_(wanted[start:start + 500])).all())
            for id_, symbol, entity_type in rows:
                if asset_type is None or norm(entity_type) == norm(asset_type):
                    found.setdefault(symbol, []).append(id_)
        return {symbol: ids[0] for symbol, ids in found.items() if len(ids) == 1}

    def get_related_entities(self, universe_id: int, target_date=None) -> list:
        """The universe's financial assets in force on ``target_date`` (all members when None), as domain entities
        of their own class: the related entities the resolution service gives a factor resolved on a Universe (a
        TradingStrategy sees every constituent through its per-entity dependencies)."""
        from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
        from src.infrastructure.models.universe.universe_financial_asset import UniverseFinancialAssetModel
        day = target_date.date() if isinstance(target_date, datetime) else target_date
        query = (self.session.query(FinancialAssetModel.id, FinancialAssetModel.entity_type)
                 .join(UniverseFinancialAssetModel, UniverseFinancialAssetModel.financial_asset_id == FinancialAssetModel.id)
                 .filter(UniverseFinancialAssetModel.universe_id == universe_id))
        if day is not None:
            query = query.filter((UniverseFinancialAssetModel.start_date.is_(None))
                                 | (UniverseFinancialAssetModel.start_date <= day),
                                 (UniverseFinancialAssetModel.end_date.is_(None))
                                 | (UniverseFinancialAssetModel.end_date >= day))
        out = []
        for asset_id, entity_type in query.order_by(FinancialAssetModel.id).all():
            repo = self.factory.get_local_repository(domain_asset_type(entity_type)) if self.factory else None
            entity = repo.get_by_id(asset_id) if repo is not None else None
            if entity is not None:
                out.append(entity)
        return out

    def stored_symbols(self, asset_type: str) -> List[str]:
        """Every stored symbol of one asset type (a domain class name, e.g. 'CompanyShare'), sorted."""
        return self.stored_assets().get(domain_asset_type(asset_type), [])

    def stored_assets(self) -> Dict[str, List[str]]:
        """{domain asset type: sorted symbols} of every stored financial asset ('company_share' -> 'CompanyShare',
        'futures' -> 'Future'): the choices of a strategy's financial-asset universe."""
        from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
        out: Dict[str, set] = {}
        for symbol, entity_type in self.session.query(FinancialAssetModel.symbol, FinancialAssetModel.entity_type):
            if symbol:
                out.setdefault(domain_asset_type(entity_type), set()).add(symbol)
        return {t: sorted(s) for t, s in sorted(out.items())}

    def company_share_sectors(self) -> Dict[str, str]:
        """{symbol: sector name} of the company shares whose company has a sector (through its industry);
        'Unclassified' left out."""
        from src.infrastructure.models.finance.company import CompanyModel
        from src.infrastructure.models.finance.financial_assets.company_share import CompanyShareModel
        from src.infrastructure.models.industry import IndustryModel
        from src.infrastructure.models.sector import SectorModel
        rows = (self.session.query(CompanyShareModel.symbol, SectorModel.name)
                .join(CompanyModel, CompanyModel.id == CompanyShareModel.company_id)
                .join(IndustryModel, IndustryModel.id == CompanyModel.industry_id)
                .join(SectorModel, SectorModel.id == IndustryModel.sector_id).all())
        return {s: n for s, n in rows if s and n and n.lower() != "unclassified"}

    def saved_universes(self) -> List[Dict[str, Any]]:
        """[{id, name, version, assets: {domain type: symbols}, factor_ids}] of the universes with members (their
        financial assets, point-in-time constituents and factors)."""
        from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
        from src.infrastructure.models.universe.universe_constituent import UniverseConstituentModel
        from src.infrastructure.models.universe.universe_factor import UniverseFactorModel
        from src.infrastructure.models.universe.universe_financial_asset import UniverseFinancialAssetModel
        assets = {i: (s, domain_asset_type(t)) for i, s, t in self.session.query(
            FinancialAssetModel.id, FinancialAssetModel.symbol, FinancialAssetModel.entity_type)}
        members: Dict[int, Dict[str, set]] = {}
        pairs = list(self.session.query(UniverseFinancialAssetModel.universe_id,
                                        UniverseFinancialAssetModel.financial_asset_id))
        pairs += list(self.session.query(UniverseConstituentModel.universe_id, UniverseConstituentModel.entity_id))
        for universe_id, asset_id in pairs:
            if asset_id in assets:
                symbol, asset_type = assets[asset_id]
                members.setdefault(universe_id, {}).setdefault(asset_type, set()).add(symbol)
        factors: Dict[int, List[int]] = {}
        for universe_id, factor_id in self.session.query(UniverseFactorModel.universe_id, UniverseFactorModel.factor_id):
            factors.setdefault(universe_id, []).append(factor_id)
        out = []
        for orm in self.session.query(UniverseModel).order_by(UniverseModel.name, UniverseModel.version):
            if orm.id in members or orm.id in factors:
                out.append({"id": orm.id, "name": orm.name, "version": orm.version,
                            "assets": {t: sorted(s) for t, s in members.get(orm.id, {}).items()},
                            "factor_ids": sorted(factors.get(orm.id, []))})
        return out

    # -- membership use cases (rules applied by the entity) -------------------------------------------------------
    def _load(self, universe_id: int) -> Universe:
        universe = self.get_by_id(universe_id)
        if universe is None:
            raise LookupError(f"universe {universe_id} does not exist")
        return universe

    def add_financial_asset(self, universe_id: int, financial_asset_id: int, start_date: Optional[date] = None,
                            end_date: Optional[date] = None) -> UniverseFinancialAsset:
        universe = self._load(universe_id)
        universe.add_financial_asset(financial_asset_id, start_date=start_date, end_date=end_date)
        stored = self.update(universe)
        return next(m for m in reversed(stored.financial_assets)
                    if m.financial_asset_id == financial_asset_id and m.start_date == start_date)

    def remove_financial_asset(self, universe_id: int, financial_asset_id: int,
                               start_date: Optional[date] = None) -> bool:
        universe = self._load(universe_id)
        removed = universe.remove_financial_asset(financial_asset_id, start_date=start_date)
        if removed:
            self.update(universe)
        return removed

    def add_factor(self, universe_id: int, factor_id: int) -> UniverseFactor:
        universe = self._load(universe_id)
        universe.add_factor(factor_id)
        stored = self.update(universe)
        return next(f for f in stored.factors if f.factor_id == factor_id)

    def remove_factor(self, universe_id: int, factor_id: int) -> bool:
        universe = self._load(universe_id)
        removed = universe.remove_factor(factor_id)
        if removed:
            self.update(universe)
        return removed
