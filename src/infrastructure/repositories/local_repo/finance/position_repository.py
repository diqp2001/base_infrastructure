"""
Position Repository – CRUD operations for Position entities.

PositionModel columns: id, portfolio_id, quantity, position_type.
Symbol-based lookups are not possible directly; navigate via Holding.position_id.
"""

from typing import List, Optional
from decimal import Decimal

from sqlalchemy.orm import Session

from src.domain.entities.finance.holding.position import Position as PositionEntity, PositionType
from src.infrastructure.models.finance.position import PositionModel
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.finance.position_mapper import PositionMapper
from src.domain.ports.finance.position_port import PositionPort

import logging

logger = logging.getLogger(__name__)


class PositionRepository(BaseLocalRepository, PositionPort):
    """Repository for Position entities.

    The underlying PositionModel carries only (portfolio_id, quantity, position_type).
    Methods that previously relied on symbol / is_active / market_value columns are
    preserved with graceful stubs so callers do not break.
    """

    def __init__(self, session: Session, factory=None, mapper: PositionMapper = None):
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or PositionMapper()
        self.logger = logger

    @property
    def model_class(self):
        return PositionModel

    def _to_entity(self, model: PositionModel) -> Optional[PositionEntity]:
        if not model:
            return None
        return self.mapper.to_domain(model)

    def _to_model(self, entity: PositionEntity) -> PositionModel:
        if not entity:
            return None
        return self.mapper.to_orm(entity)

    # ------------------------------------------------------------------
    # Standard reads
    # ------------------------------------------------------------------

    def get_all(self) -> List[PositionEntity]:
        models = self.session.query(PositionModel).all()
        return [self._to_entity(m) for m in models]

    def get_by_id(self, position_id: int) -> Optional[PositionEntity]:
        model = self.session.query(PositionModel).filter(
            PositionModel.id == position_id
        ).first()
        return self._to_entity(model)

    def get_by_portfolio_id(self, portfolio_id: int) -> List[PositionEntity]:
        models = self.session.query(PositionModel).filter(
            PositionModel.portfolio_id == portfolio_id
        ).all()
        return [self._to_entity(m) for m in models]

    # ------------------------------------------------------------------
    # Symbol-based stubs (PositionModel has no symbol column)
    # Navigate via HoldingModel.position_id for symbol lookups.
    # ------------------------------------------------------------------

    def get_by_symbol(self, symbol: str) -> List[PositionEntity]:
        return []

    def get_by_portfolio_and_symbol(
        self, portfolio_id: int, symbol: str
    ) -> Optional[PositionEntity]:
        return None

    def exists_position(self, portfolio_id: int, symbol: str) -> bool:
        return False

    def get_by_asset_type(self, asset_type: str) -> List[PositionEntity]:
        return []

    def get_active_positions(self) -> List[PositionEntity]:
        """Return all non-zero quantity positions (no is_active column on model)."""
        models = self.session.query(PositionModel).filter(
            PositionModel.quantity != 0
        ).all()
        return [self._to_entity(m) for m in models]

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def add(self, entity: PositionEntity) -> Optional[PositionEntity]:
        try:
            model = self._to_model(entity)
            self.session.add(model)
            self.session.commit()
            return self._to_entity(model)
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"PositionRepository.add failed: {e}")
            return None

    def update(self, position_id: int, **kwargs) -> Optional[PositionEntity]:
        """Update quantity and/or position_type — the only mutable columns."""
        try:
            model = self.session.query(PositionModel).filter(
                PositionModel.id == position_id
            ).first()
            if not model:
                return None

            allowed = {'quantity', 'position_type'}
            for attr, value in kwargs.items():
                if attr in allowed:
                    setattr(model, attr, value)

            self.session.commit()
            return self._to_entity(model)
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"PositionRepository.update {position_id} failed: {e}")
            return None

    def update_quantity(
        self, position_id: int, new_quantity: float, new_average_cost: float = None
    ) -> Optional[PositionEntity]:
        """Update position quantity (average_cost is not persisted on this model)."""
        return self.update(position_id, quantity=int(new_quantity))

    def update_price(self, position_id: int, new_price: float) -> Optional[PositionEntity]:
        """No-op: PositionModel has no price column."""
        return self.get_by_id(position_id)

    def close_position(self, position_id: int) -> Optional[PositionEntity]:
        """Zero-out quantity to represent a closed position."""
        return self.update(position_id, quantity=0)

    def delete(self, position_id: int) -> bool:
        try:
            model = self.session.query(PositionModel).filter(
                PositionModel.id == position_id
            ).first()
            if not model:
                return False
            self.session.delete(model)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"PositionRepository.delete {position_id} failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Create-or-get
    # ------------------------------------------------------------------

    def _get_next_available_position_id(self) -> int:
        result = self.session.query(PositionModel.id).order_by(PositionModel.id.desc()).first()
        return (result[0] + 1) if result else 1

    def _create_or_get(self, portfolio_id: int, **kwargs) -> Optional[PositionEntity]:
        """
        Create a new Position for the given portfolio.

        Accepts:
            quantity      int   (default 0)
            position_type str or PositionType  (default LONG)
        """
        try:
            quantity = int(kwargs.get('quantity', 0))
            pt_raw = kwargs.get('position_type', PositionType.LONG)
            if isinstance(pt_raw, str):
                try:
                    position_type = PositionType[pt_raw.upper()]
                except KeyError:
                    position_type = PositionType.LONG
            else:
                position_type = pt_raw

            entity = PositionEntity(
                id=None,
                quantity=quantity,
                position_type=position_type,
            )
            entity.portfolio_id = portfolio_id

            model = self.mapper.to_orm(entity)
            self.session.add(model)
            self.session.commit()

            self.logger.info(
                f"Created Position id={model.id} portfolio={portfolio_id} qty={quantity}"
            )
            return self.mapper.to_domain(model)

        except Exception as e:
            self.session.rollback()
            self.logger.error(
                f"PositionRepository._create_or_get portfolio={portfolio_id} failed: {e}"
            )
            return None

    def get_or_create(
        self,
        portfolio_id: int,
        symbol: str,
        asset_type: Optional[str] = None,
        asset_id: Optional[int] = None,
        quantity: Optional[float] = None,
        average_cost: Optional[float] = None,
    ) -> Optional[PositionEntity]:
        """Compatibility shim — creates a new position (symbol not stored on model)."""
        return self._create_or_get(portfolio_id=portfolio_id, quantity=quantity or 0)

    # ------------------------------------------------------------------
    # Aggregate stubs (no financial value columns on model)
    # ------------------------------------------------------------------

    def get_portfolio_value(self, portfolio_id: int) -> Decimal:
        return Decimal('0')

    def get_portfolio_unrealized_pnl(self, portfolio_id: int) -> Decimal:
        return Decimal('0')

    # Standard CRUD alias
    def create(self, entity: PositionEntity) -> Optional[PositionEntity]:
        return self.add(entity)
