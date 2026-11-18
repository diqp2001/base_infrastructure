from sqlalchemy.orm import Session
from typing import Optional, List

from src.domain.entities.finance.holding.etf_share_option_portfolio_holding import ETFShareOptionPortfolioHolding
from src.domain.ports.finance.holding.etf_share_option_portfolio_holding_port import ETFShareOptionPortfolioHoldingPort
from src.infrastructure.repositories.mappers.finance.holding.etf_share_option_portfolio_holding_mapper import ETFShareOptionPortfolioHoldingMapper


class ETFShareOptionPortfolioHoldingRepository(ETFShareOptionPortfolioHoldingPort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = ETFShareOptionPortfolioHoldingMapper()

    @property
    def entity_class(self):
        return self.mapper.entity_class

    @property
    def model_class(self):
        return self.mapper.model_class

    # -------------------------
    # CREATE OR GET
    # -------------------------
    def _create_or_get(self, portfolio_id: int, asset_id: int, **kwargs) -> Optional[ETFShareOptionPortfolioHolding]:

        try:
            existing = self.get_by_portfolio_and_asset(portfolio_id, asset_id)
            if existing:
                return existing

            # In practice, you'd need to create the entity with proper relationships
            # This is a simplified example
            entity = ETFShareOptionPortfolioHolding(
                id=None,
                asset=None,  # Would resolve ETFShareOption by asset_id
                portfolio=None,  # Would resolve PortfolioETFShareOption by portfolio_id
                position=None,  # Would create/resolve Position
                start_date=kwargs.get("start_date"),
                end_date=kwargs.get("end_date"),
            )

            orm_obj = self.mapper.to_model(entity)

            self.session.add(orm_obj)
            self.session.commit()

            return self.mapper.to_entity(orm_obj)

        except Exception as e:
            print(f"Error creating portfolio ETF share option holding: {e}")
            return None

    # -------------------------
    # STANDARD METHODS
    # -------------------------
    def get_by_portfolio_and_asset(self, portfolio_id: int, asset_id: int) -> Optional[ETFShareOptionPortfolioHolding]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.etf_share_option_portfolio_id == portfolio_id)\
            .filter(self.model_class.etf_share_option_id == asset_id)\
            .one_or_none()
        return self.mapper.to_entity(obj)

    def get_by_id(self, id: int) -> Optional[ETFShareOptionPortfolioHolding]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == id)\
            .one_or_none()
        return self.mapper.to_entity(obj)

    def get_by_portfolio_id(self, portfolio_id: int) -> List[ETFShareOptionPortfolioHolding]:
        objs = self.session.query(self.model_class)\
            .filter(self.model_class.etf_share_option_portfolio_id == portfolio_id)\
            .all()
        return [self.mapper.to_entity(o) for o in objs]

    def get_related_entities(self, holding_id: int) -> list:
        """Return [ETFShareOption] for the option held — used by the resolution service."""
        try:
            orm = self.session.query(self.model_class).filter(self.model_class.id == holding_id).one_or_none()
            if orm is None or not orm.etf_share_option_id:
                return []
            option_repo = self.factory.get_local_repository('ETFShareOption') if self.factory else None
            if option_repo:
                option = option_repo.get_by_id(orm.etf_share_option_id)
                return [option] if option else []
            return []
        except Exception as e:
            print(f"Error getting related entities for ESO holding {holding_id}: {e}")
            return []

    def get_related_asset(self, holding_id: int):
        """The ETFShareOption held (has .multiplier) — the resolution service's 'Asset.<attribute>' deps."""
        related = self.get_related_entities(holding_id)
        return related[0] if related else None

    def get_related_position(self, holding_id: int):
        """Return the PositionModel for this holding (has .quantity) — used by the resolution service."""
        try:
            orm = self.session.query(self.model_class).filter(self.model_class.id == holding_id).one_or_none()
            return orm.position_rel if orm else None
        except Exception as e:
            print(f"Error getting position for ESO holding {holding_id}: {e}")
            return None

    def get_all(self) -> List[ETFShareOptionPortfolioHolding]:
        objs = self.session.query(self.model_class).all()
        return [self.mapper.to_entity(o) for o in objs]

    def add(self, entity: ETFShareOptionPortfolioHolding) -> Optional[ETFShareOptionPortfolioHolding]:
        obj = self.mapper.to_model(entity)
        self.session.add(obj)
        self.session.commit()
        return self.mapper.to_entity(obj)

    def update(self, entity: ETFShareOptionPortfolioHolding) -> Optional[ETFShareOptionPortfolioHolding]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == entity.id)\
            .one_or_none()

        if not obj:
            return None

        obj.start_date = entity.start_date
        obj.end_date = entity.end_date

        self.session.commit()
        return self.mapper.to_entity(obj)

    def delete(self, id: int) -> bool:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == id)\
            .one_or_none()

        if not obj:
            return False

        self.session.delete(obj)
        self.session.commit()
        return True