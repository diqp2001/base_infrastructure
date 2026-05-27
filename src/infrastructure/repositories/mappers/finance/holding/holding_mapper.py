"""
Mappers for converting between holding domain entities and infrastructure models
"""
from typing import Optional

from src.domain.entities.finance.holding.holding import Holding
from src.domain.entities.finance.holding.position import Position, PositionType
from src.infrastructure.models.finance.holding.holding import HoldingModel


class HoldingMapper:
    """Mapper for converting between holding entities and models"""

    def to_entity(self, model: Optional[HoldingModel]) -> Optional[Holding]:
        """Convert HoldingModel to Holding domain entity"""
        if not model:
            return None

        asset = type('_AssetRef', (), {
            'id': model.asset_id,
            'name': None,
            'symbol': None,
            'asset_type': 'unknown',
        })()

        container = type('_ContainerRef', (), {'id': model.container_id})()

        # Use the real position loaded via the FK relationship when available.
        # Fall back to a placeholder only when the link is not yet set.
        pos_model = getattr(model, 'position_rel', None)
        if pos_model is not None:
            position = Position(
                id=pos_model.id,
                quantity=pos_model.quantity,
                position_type=pos_model.position_type,
            )
            position.portfolio_id = pos_model.portfolio_id
            position.holding_id = getattr(pos_model, 'holding_id', None)
        else:
            position = Position(
                id=None,
                quantity=0,
                position_type=PositionType.LONG,
                asset_id=model.asset_id,
            )

        return Holding(
            id=model.id,
            asset=asset,
            container=container,
            position=position,
            start_date=model.start_date,
            end_date=model.end_date,
        )

    def to_model(self, entity: Holding) -> HoldingModel:
        """Convert Holding domain entity to HoldingModel"""
        return HoldingModel(
            id=entity.id,
            asset_id=entity.asset.id,
            container_id=entity.container.id,
            start_date=entity.start_date,
            end_date=entity.end_date,
        )
