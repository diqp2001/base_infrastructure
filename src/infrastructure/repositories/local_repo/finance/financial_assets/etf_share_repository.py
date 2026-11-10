"""
ETFShare Repository for local database operations. Currency / exchange resolution is inherited from
ShareRepository (shared with CompanyShareRepository).
"""

from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from src.domain.entities.finance.financial_assets.share.etf_share.etf_share import ETFShare as ETFShareEntity
from src.domain.ports.finance.financial_assets.share.etf_share.etf_share_port import ETFSharePort
from src.infrastructure.models.finance.financial_assets.etf_share import ETFShareModel
from src.infrastructure.repositories.local_repo.finance.financial_assets.share_repository import ShareRepository
from src.infrastructure.repositories.mappers.finance.financial_assets.share.etf_share.etf_share_mapper import ETFShareMapper


class ETFShareRepository(ShareRepository, ETFSharePort):
    def __init__(self, session: Session, factory=None):
        super().__init__(session, factory)
        self.mapper = ETFShareMapper()

    @property
    def model_class(self):
        return self.mapper.model_class

    @property
    def entity_class(self):
        return self.mapper.entity_class

    def _to_entity(self, infra: ETFShareModel) -> Optional[ETFShareEntity]:
        return self.mapper.to_domain(infra) if infra else None

    def _to_model(self, entity: ETFShareEntity) -> Optional[ETFShareModel]:
        return self.mapper.to_orm(entity) if entity else None

    def get_all(self) -> List[ETFShareEntity]:
        return [self._to_entity(m) for m in self.session.query(ETFShareModel).all()]

    def get_by_id(self, etf_share_id: int) -> Optional[ETFShareEntity]:
        return self._to_entity(self.session.query(ETFShareModel).filter(ETFShareModel.id == etf_share_id).first())

    def get_by_symbol(self, symbol: str) -> Optional[ETFShareEntity]:
        return self._to_entity(self.session.query(ETFShareModel).filter(ETFShareModel.symbol == symbol).first())

    def get_by_issuer(self, issuer: str) -> List[ETFShareEntity]:
        return [self._to_entity(m) for m in
                self.session.query(ETFShareModel).filter(ETFShareModel.issuer == issuer).all()]

    def add(self, etf_share: ETFShareEntity) -> ETFShareEntity:
        """Add an ETF share; the stored one when the ticker already exists (tickers are unique per ETF)."""
        existing = self.get_by_symbol(etf_share.symbol)
        if existing:
            return existing
        model = self.mapper.to_orm(etf_share)
        self.session.add(model)
        self.session.commit()
        return self._to_entity(model)

    def update(self, etf_share_id: int, **kwargs) -> Optional[ETFShareEntity]:
        model = self.session.query(ETFShareModel).filter(ETFShareModel.id == etf_share_id).first()
        if not model:
            return None
        for attr, value in kwargs.items():
            if hasattr(model, attr):
                setattr(model, attr, value)
        self.session.commit()
        return self._to_entity(model)

    # ---- constituents: the ETF's holdings, point in time ----
    @staticmethod
    def holdings_universe_name(symbol: str) -> str:
        """The Universe holding an ETF's constituents (UniverseConstituent rows: weight, start_date, end_date)."""
        return f"{symbol.upper()} holdings"

    def _holdings(self, etf_share_id: int, target_date) -> list:
        """The UniverseConstituent rows of the ETF's holdings universe in force on target_date."""
        etf = self.get_by_id(etf_share_id)
        if etf is None or self.factory is None:
            return []
        universe = self.factory.get_local_repository('InvestmentUniverse').get_by_name(self.holdings_universe_name(etf.symbol))
        if universe is None:
            return []
        day = target_date.date() if hasattr(target_date, 'date') and callable(target_date.date) else target_date
        return self.factory.get_local_repository('UniverseConstituent').get_active_by_universe(
            universe.id, day or date.today())

    def get_related_entities(self, etf_share_id: int, target_date=None) -> list:
        """The ETF's constituents in force on target_date (the resolution service's related entities)."""
        out = []
        for row in self._holdings(etf_share_id, target_date):
            repo = self.factory.get_local_repository(row.entity_type)
            entity = repo.get_by_id(row.entity_id) if repo is not None else None
            if entity is not None:
                out.append(entity)
        return out

    def get_related_weights(self, etf_share_id: int, target_date=None) -> dict:
        """{constituent symbol: weight} of the ETF's holdings in force on target_date (not normalized)."""
        out = {}
        for row in self._holdings(etf_share_id, target_date):
            repo = self.factory.get_local_repository(row.entity_type)
            entity = repo.get_by_id(row.entity_id) if repo is not None else None
            if entity is not None and row.weight is not None:
                out[entity.symbol] = float(row.weight)
        return out

    def _create_or_get(self, symbol: str, exchange_id: Optional[int] = None, currency: str = 'USD',
                       name: Optional[str] = None, issuer: Optional[str] = None,
                       asset_class: Optional[str] = None, leverage_factor: float = 1.0,
                       replication: Optional[str] = None, exchange_name: Optional[str] = None,
                       start_date: Optional[date] = None, end_date: Optional[date] = None) -> Optional[ETFShareEntity]:
        """The stored ETF share for this ticker, else a new one with its currency and exchange resolved."""
        existing = self.get_by_symbol(symbol)
        if existing:
            return existing
        if exchange_id is None:
            exchange_id = self._resolve_exchange_dependency(symbol, exchange_name)
        currency_id = self._resolve_currency_id(currency)
        if currency_id is None or exchange_id is None:
            print(f"Error creating ETF share for {symbol}: currency ({currency_id}) or exchange ({exchange_id}) "
                  f"could not be resolved")
            return None
        try:
            return self.add(ETFShareEntity(
                id=None, symbol=symbol, currency_id=currency_id, exchange_id=exchange_id, name=name,
                issuer=issuer, asset_class=asset_class, leverage_factor=leverage_factor, replication=replication,
                start_date=start_date or date.today(), end_date=end_date,
            ))
        except Exception as e:
            self.session.rollback()
            print(f"Error creating ETF share for {symbol}: {e}")
            return None
