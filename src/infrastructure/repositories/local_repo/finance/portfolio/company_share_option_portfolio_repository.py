from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date
from src.domain.entities.finance.portfolio.company_share_option_portfolio import CompanyShareOptionPortfolio
from src.domain.ports.finance.portfolio.company_share_option_portfolio_port import CompanyShareOptionPortfolioPort
from src.infrastructure.repositories.mappers.finance.portfolio.company_share_option_portfolio_mapper import CompanyShareOptionPortfolioMapper


class CompanyShareOptionPortfolioRepository(CompanyShareOptionPortfolioPort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = CompanyShareOptionPortfolioMapper()

    @property
    def entity_class(self):
        return self.mapper.entity_class
    @property
    def model_class(self):
        return self.mapper.model_class
    def _to_entity(self, model) :
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        return self.mapper.to_domain(model)
    
    def _to_model(self, entity):
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        return self.mapper.to_orm(entity)
    # -------------------------
    # CREATE OR GET
    # -------------------------
    
    def _create_or_get(self, name: str, **kwargs) -> Optional[CompanyShareOptionPortfolio]:

        try:
            existing = self.get_by_name(name)
            if existing:
                return existing

            entity = CompanyShareOptionPortfolio(
                id=None,
                name=name,
                start_date=kwargs.get("start_date", datetime.now()),
                end_date=kwargs.get("end_date"),
            )

            orm_obj = self.mapper.to_orm(entity)

            self.session.add(orm_obj)
            self.session.commit()

            return self.mapper.to_domain(orm_obj)

        except Exception as e:
            print(f"Error creating portfolio company share option {name}: {e}")
            return None

    # -------------------------
    # STANDARD METHODS
    # -------------------------
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionPortfolio]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.name == name)\
            .one_or_none()
        return self.mapper.to_domain(obj) if obj else None

    def get_by_id(self, id: int) -> Optional[CompanyShareOptionPortfolio]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == id)\
            .one_or_none()
        return self.mapper.to_domain(obj)

    def get_all(self) -> List[CompanyShareOptionPortfolio]:
        objs = self.session.query(self.model_class).all()
        return [self.mapper.to_domain(o) for o in objs]

    def add(self, entity: CompanyShareOptionPortfolio) -> Optional[CompanyShareOptionPortfolio]:
        obj = self.mapper.to_orm(entity)
        self.session.add(obj)
        self.session.commit()
        return self.mapper.to_domain(obj)

    def update(self, entity: CompanyShareOptionPortfolio) -> Optional[CompanyShareOptionPortfolio]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == entity.id)\
            .one_or_none()

        if not obj:
            return None

        obj.name = entity.name
        obj.start_date = entity.start_date
        obj.end_date = entity.end_date

        self.session.commit()
        return self.mapper.to_domain(obj)

    def delete(self, id: int) -> bool:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == id)\
            .one_or_none()

        if not obj:
            return False

        self.session.delete(obj)
        self.session.commit()
        return True

    def get_related_entities(self, portfolio_id: int) -> List:
        """Return the CompanyShareOptionPortfolioHolding entities for this sub-portfolio."""
        try:
            if self.factory:
                holding_repo = self.factory.get_local_repository('CompanyShareOptionPortfolioHolding')
                if holding_repo:
                    return holding_repo.get_by_portfolio_id(portfolio_id) or []
            return []
        except Exception as e:
            print(f"Error retrieving holdings for CompanyShareOptionPortfolio {portfolio_id}: {e}")
            return []

    # ------------------------------------------------------------------
    # Sub-portfolio wiring — called by UnifiedPortfolioManager
    # ------------------------------------------------------------------

    def ensure_sub_portfolio_linked(self, main_portfolio, now) -> Optional[int]:
        """Idempotently create (or retrieve) the CompanyShareOptionPortfolio sub-portfolio
        and ensure it is linked to main_portfolio via a CompanyShareOptionPortfolioPortfolioHolding row.
        Returns the sub-portfolio id, or None on failure."""
        from src.infrastructure.models.finance.holding.company_share_option_portfolio_portfolio_holding import (
            CompanyShareOptionPortfolioPortfolioHoldingModel,
        )

        main_id = main_portfolio.id
        sub_name = f"{main_portfolio.name}_CSO"

        sub_portfolio = self._create_or_get(name=sub_name)
        if sub_portfolio is None:
            return None
        sub_portfolio_id = sub_portfolio.id

        link = (
            self.session.query(CompanyShareOptionPortfolioPortfolioHoldingModel)
            .filter_by(container_id=main_id, asset_id=sub_portfolio_id)
            .first()
        )
        if not link:
            self.session.add(CompanyShareOptionPortfolioPortfolioHoldingModel(
                holding_type="CompanyShareOptionPortfolioPortfolioHoldings",
                asset_id=sub_portfolio_id,
                container_id=main_id,
                portfolio_id=main_id,
                start_date=now,
            ))
            self.session.commit()

        return sub_portfolio_id

    def ensure_ticker_holding(self, ticker: str, sub_portfolio_id: int, now) -> None:
        """Idempotently create a CompanyShareOptionPortfolioHolding + Position for ticker."""
        from src.infrastructure.models.finance.financial_assets.derivative.option.company_share_option import (
            CompanyShareOptionModel,
        )
        from src.infrastructure.models.finance.holding.company_share_option_portfolio_holding import (
            CompanyShareOptionPortfolioHoldingModel,
        )
        from src.infrastructure.models.finance.position import PositionModel

        option = self.session.query(CompanyShareOptionModel).filter_by(symbol=ticker).first()
        if not option:
            return

        existing = (
            self.session.query(CompanyShareOptionPortfolioHoldingModel)
            .filter_by(company_share_option_portfolio_id=sub_portfolio_id, company_share_option_id=option.id)
            .first()
        )
        if not existing:
            pos = PositionModel(portfolio_id=sub_portfolio_id, quantity=0, position_type='LONG')
            self.session.add(pos)
            self.session.flush()
            self.session.add(CompanyShareOptionPortfolioHoldingModel(
                asset_id=option.id,
                company_share_option_id=option.id,
                company_share_option_portfolio_id=sub_portfolio_id,
                portfolio_id=sub_portfolio_id,
                container_id=sub_portfolio_id,
                start_date=now,
                position_id=pos.id,
            ))
            self.session.commit()

    def update_option_holding_quantity(self, ticker: str, new_quantity: float) -> bool:
        """Update the PositionModel.quantity linked to the CSO holding for `ticker`.

        Called from UnifiedPortfolioManager.update_holding_position so the resolution
        service (which reads position_rel.quantity) sees the current fill quantity.
        """
        from src.infrastructure.models.finance.financial_assets.derivative.option.company_share_option import (
            CompanyShareOptionModel,
        )
        from src.infrastructure.models.finance.holding.company_share_option_portfolio_holding import (
            CompanyShareOptionPortfolioHoldingModel,
        )
        from src.infrastructure.models.finance.position import PositionModel

        try:
            option = self.session.query(CompanyShareOptionModel).filter_by(symbol=ticker).first()
            if not option:
                return False
            holding = (
                self.session.query(CompanyShareOptionPortfolioHoldingModel)
                .filter_by(company_share_option_id=option.id)
                .first()
            )
            if not holding or not holding.position_id:
                return False
            position = self.session.query(PositionModel).filter_by(id=holding.position_id).first()
            if not position:
                return False
            position.quantity = new_quantity
            self.session.commit()
            return True
        except Exception as e:
            print(f"Error updating option holding quantity for {ticker}: {e}")
            return False

    def find_ticker_sub_portfolio_id(self, ticker: str) -> Optional[int]:
        """Return the sub-portfolio id for an already-held CompanyShareOption ticker, or None."""
        from src.infrastructure.models.finance.financial_assets.derivative.option.company_share_option import (
            CompanyShareOptionModel,
        )
        from src.infrastructure.models.finance.holding.company_share_option_portfolio_holding import (
            CompanyShareOptionPortfolioHoldingModel,
        )
        option = self.session.query(CompanyShareOptionModel).filter_by(symbol=ticker).first()
        if not option:
            return None
        holding = (
            self.session.query(CompanyShareOptionPortfolioHoldingModel)
            .filter_by(company_share_option_id=option.id)
            .first()
        )
        return holding.company_share_option_portfolio_id if holding else None