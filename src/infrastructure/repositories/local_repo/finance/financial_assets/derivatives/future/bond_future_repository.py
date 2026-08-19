import os
from typing import Optional
from sqlalchemy.orm import Session

from src.domain.entities.finance.financial_assets.derivatives.future.bond_future import BondFuture
from src.domain.ports.finance.financial_assets.derivatives.future.bond_future_port import BondFuturePort
from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.future.future_repository import FutureRepository
from src.infrastructure.repositories.mappers.finance.financial_assets.derivatives.future.bond_future_mapper import BondFutureMapper


class BondFutureRepository(FutureRepository, BondFuturePort):
    """Local repository for BondFuture entities, backed by the futures table."""

    def __init__(self, session: Session, factory=None):
        super().__init__(session, factory, mapper=BondFutureMapper())

    @property
    def entity_class(self):
        return self.mapper.entity_class

    @property
    def model_class(self):
        return self.mapper.model_class

    def get_by_symbol(self, symbol: str) -> Optional[BondFuture]:
        try:
            orm_obj = (
                self.session.query(self.model_class)
                .filter(self.model_class.symbol == symbol)
                .first()
            )
            return self.mapper.to_domain(orm_obj)
        except Exception as e:
            print(f"Error retrieving BondFuture by symbol {symbol}: {e}_{os.path.abspath(__file__)}")
            return None

    def add(self, entity: BondFuture) -> Optional[BondFuture]:
        try:
            orm_obj = self.mapper.to_orm(entity)
            self.session.add(orm_obj)
            self.session.commit()
            self.session.refresh(orm_obj)
            return self.mapper.to_domain(orm_obj)
        except Exception as e:
            self.session.rollback()
            print(f"Error adding BondFuture: {e}_{os.path.abspath(__file__)}")
            return None

    def _create_or_get(self, symbol: str, **kwargs) -> Optional[BondFuture]:
        existing = self.get_by_symbol(symbol)
        if existing:
            return existing
        try:
            entity = BondFuture(
                id=None,
                name=kwargs.get('name') or f"{symbol} Bond Future",
                symbol=symbol,
                currency_id=kwargs.get('currency_id'),
                exchange_id=kwargs.get('exchange_id'),
                underlying_asset_id=kwargs.get('underlying_asset_id'),
                contract_size=kwargs.get('contract_size'),
            )
            return self.add(entity)
        except Exception as e:
            print(f"Error in _create_or_get BondFuture {symbol}: {e}_{os.path.abspath(__file__)}")
            return None
