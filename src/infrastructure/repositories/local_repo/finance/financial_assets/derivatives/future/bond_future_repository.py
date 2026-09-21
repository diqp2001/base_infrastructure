import os
from datetime import date as _date
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

    # SOFR/CORRA quarterly months — same convention as IBKR local_symbol suffix
    _QUARTERLY_MONTH_CODES = {3: 'H', 6: 'M', 9: 'U', 12: 'Z'}

    @staticmethod
    def front_month_symbol(root: str, target_date: _date) -> str:
        """Return the IBKR local_symbol for the front-month futures contract.

        Uses the same root+month_code+year_digit convention that IBKR uses for
        CME quarterly futures (e.g. SR3U6 for Sep-2026, SR3Z6 for Dec-2026).
        Expiry is approximated as the 21st of the contract month (3rd-Wednesday proxy).
        """
        q_months = sorted(BondFutureRepository._QUARTERLY_MONTH_CODES.keys())
        year = target_date.year
        for q_month in q_months:
            if q_month >= target_date.month:
                approx_expiry = _date(year, q_month, 21)
                if approx_expiry > target_date:
                    code = BondFutureRepository._QUARTERLY_MONTH_CODES[q_month]
                    return f"{root}{code}{str(year)[-1]}"
        # Roll to next year March
        code = BondFutureRepository._QUARTERLY_MONTH_CODES[3]
        return f"{root}{code}{str(year + 1)[-1]}"

    def get_by_root_symbol(self, root: str, target_date: Optional[_date] = None) -> Optional[BondFuture]:
        """Return the front-month BondFuture for root symbol and target_date.

        When target_date is provided, looks for the contract matching the expected
        front-month symbol (e.g. SR3U6 for Sep-2026).  Falls back to any matching
        contract if the exact symbol is not found.
        """
        try:
            if target_date is not None:
                symbol = self.front_month_symbol(root, target_date)
                orm_obj = (
                    self.session.query(self.model_class)
                    .filter(self.model_class.symbol == symbol)
                    .first()
                )
                if orm_obj:
                    return self.mapper.to_domain(orm_obj)
            # Fallback: any contract with this root
            orm_obj = (
                self.session.query(self.model_class)
                .filter(self.model_class.symbol.like(f"{root}%"))
                .first()
            )
            return self.mapper.to_domain(orm_obj)
        except Exception as e:
            print(f"Error retrieving BondFuture by root symbol {root}: {e}_{os.path.abspath(__file__)}")
            return None

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
