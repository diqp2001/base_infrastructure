"""
Mappers for converting between holding domain entities and infrastructure models
"""
from typing import Optional

from src.domain.entities.finance.holding.holding import Holding
from src.domain.entities.finance.holding.position import Position, PositionType
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset
from src.domain.entities.finance.portfolio.portfolio import Portfolio
from src.infrastructure.models.finance.holding.holding import HoldingModel
from src.infrastructure.repositories.mappers.finance.position_mapper import PositionMapper


class HoldingMapper:
    """Mapper for converting between holding entities and models"""

    @property
    def discriminator(self):
        return "Holding"

    @property
    def asset_class(self):
        #parent class will have has asset many types of portfolio, so we return the base class here. Subclasses will override this to return the specific asset type.
        return Portfolio

    @property
    def container_class(self):
        return Portfolio

    @property
    def entity_class(self):
        return Holding

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
            position = PositionMapper.to_domain(pos_model)
        

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
            holding_type=self.discriminator,
            asset_id=entity.asset.id,
            container_id=entity.container.id,
            start_date=entity.start_date,
            end_date=entity.end_date,
        )
