from sqlalchemy.orm import Session
from typing import Dict, Optional, List
from datetime import datetime, date
from src.infrastructure.models.finance.portfolio.company_share_portfolio import CompanySharePortfolioModel
from src.domain.entities.finance.portfolio.company_share_portfolio import CompanySharePortfolio
from src.infrastructure.repositories.mappers.finance.portfolio.company_share_portfolio_mapper import CompanySharePortfolioMapper
from src.domain.ports.finance.portfolio.company_share_portfolio_port import CompanySharePortfolioPort


class CompanySharePortfolioRepository(CompanySharePortfolioPort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = CompanySharePortfolioMapper()

    @property
    def entity_class(self):
        return self.mapper.entity_class
    @property
    def model_class(self):
        return self.mapper.model_class

    # -------------------------
    # CREATE OR GET
    # -------------------------
    def _create_or_get(self, name_or_cls=None, name_str=None, **kwargs) -> Optional[CompanySharePortfolio]:
        # Resolve name from whichever calling form was used:
        #   _create_or_get('Large_US_BANK')           → name_or_cls is the str
        #   _create_or_get(EntityCls, 'Large_US_BANK') → name_or_cls is the class, name_str has it
        #   _create_or_get(name='Large_US_BANK')       → name_or_cls=None, name in kwargs
        if isinstance(name_or_cls, str):
            name = name_or_cls
        elif name_str is not None:
            name = name_str
        else:
            name = kwargs.get('name')

        try:
            existing = self.get_by_name(name)
            if existing:
                return existing

            entity = self.entity_class(
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
            self.session.rollback()
            print(f"Error creating portfolio company share option {name}: {e}")
            return None

    # -------------------------
    # STANDARD METHODS
    # -------------------------
    
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolio]:
        """Retrieve a portfolio by name."""
        model = self.session.query(CompanySharePortfolioModel).filter(
            CompanySharePortfolioModel.name == name
        ).first()
        return self.mapper.to_domain(model)  if model else None

    def get_by_id(self, id: int) -> Optional[CompanySharePortfolio]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == id)\
            .one_or_none()
        return self.mapper.to_domain(obj)

    def get_all(self) -> List[CompanySharePortfolio]:
        objs = self.session.query(self.model_class).all()
        return [self.mapper.to_domain(o) for o in objs]

    def add(self, entity: CompanySharePortfolio) -> Optional[CompanySharePortfolio]:
        obj = self.mapper.to_orm(entity)
        self.session.add(obj)
        self.session.commit()
        return self.mapper.to_domain(obj)

    def update(self, entity: CompanySharePortfolio) -> Optional[CompanySharePortfolio]:
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

    def set_holding_for_entity(self, portfolio_id: int, asset_id: int) -> None:
        """Idempotently create a holding for a single asset in this portfolio."""
        from src.infrastructure.models.finance.holding.company_share_portfolio_holding import CompanySharePortfolioHoldingModel as _HoldingModel
        existing = self.session.query(_HoldingModel).filter(
            _HoldingModel.company_share_portfolio_id == portfolio_id,
            _HoldingModel.asset_id == asset_id
        ).first()
        if not existing:
            self.session.add(_HoldingModel(
                holding_type="CompanySharePortfolioHoldings",
                asset_id=asset_id,
                container_id=portfolio_id,
                company_share_portfolio_id=portfolio_id,
                start_date=datetime.now(),
            ))
            self.session.commit()

    def set_holdings(self, portfolio_config: Dict) -> None:
        """Create holdings for each component if they do not already exist."""
        name = portfolio_config.get('name')
        if not name:
            return

        portfolio = self._create_or_get(name)
        if not portfolio:
            return

        for component_class, tickers in portfolio_config.get('components', {}).items():
            component_repo = self.factory.get_local_repository(component_class)
            for ticker in tickers:
                share = component_repo.get_by_symbol(ticker)
                if share:
                    self.set_holding_for_entity(portfolio.id, share.id)

    def get_related_entities(self, portfolio_id: int) -> List:
        """Return all CompanySharePortfolioHoldings for this portfolio."""
        try:
            from src.infrastructure.repositories.local_repo.finance.holding.company_share_portfolio_holding_repository import CompanySharePortfolioHoldingRepository
            return CompanySharePortfolioHoldingRepository(self.session, self.factory).get_holdings_by_portfolio_id(portfolio_id)
        except Exception as e:
            print(f"Error retrieving holdings for CompanySharePortfolio {portfolio_id}: {e}")
            return []

    # ------------------------------------------------------------------
    # Sub-portfolio wiring — called by UnifiedPortfolioManager
    # ------------------------------------------------------------------

    def ensure_sub_portfolio_linked(self, main_portfolio, now) -> Optional[int]:
        """Idempotently create (or retrieve) the CompanySharePortfolio sub-portfolio
        and ensure it is linked to main_portfolio via a CompanySharePortfolioPortfolioHolding row.
        Returns the sub-portfolio id, or None on failure."""
        from src.infrastructure.models.finance.holding.company_share_portfolio_portfolio_holding import (
            CompanySharePortfolioPortfolioHoldingModel,
        )
        from src.infrastructure.models.finance.position import PositionModel

        main_id = main_portfolio.id
        sub_name = f"{main_portfolio.name}_CS"

        sub_portfolio = self._create_or_get(name=sub_name)
        if sub_portfolio is None:
            return None
        sub_portfolio_id = sub_portfolio.id

        link = (
            self.session.query(CompanySharePortfolioPortfolioHoldingModel)
            .filter_by(container_id=main_id)
            .first()
        )
        if not link:
            pp_pos = PositionModel(portfolio_id=main_id, quantity=1, position_type='LONG')
            self.session.add(pp_pos)
            self.session.flush()
            self.session.add(CompanySharePortfolioPortfolioHoldingModel(
                asset_id=sub_portfolio_id,
                portfolio_id=main_id,
                container_id=main_id,
                start_date=now,
                position_id=pp_pos.id,
            ))
            self.session.commit()

        return sub_portfolio_id

    def ensure_ticker_holding(self, ticker: str, sub_portfolio_id: int, now) -> None:
        """Idempotently create a CompanySharePortfolioHolding + Position for ticker."""
        from src.infrastructure.models.finance.financial_assets.company_share import CompanyShareModel
        from src.infrastructure.models.finance.holding.company_share_portfolio_holding import (
            CompanySharePortfolioHoldingModel,
        )
        from src.infrastructure.models.finance.position import PositionModel

        share = self.session.query(CompanyShareModel).filter_by(symbol=ticker).first()
        if not share:
            return

        existing = (
            self.session.query(CompanySharePortfolioHoldingModel)
            .filter_by(company_share_portfolio_id=sub_portfolio_id, asset_id=share.id)
            .first()
        )
        if not existing:
            pos = PositionModel(portfolio_id=sub_portfolio_id, quantity=0, position_type='LONG')
            self.session.add(pos)
            self.session.flush()
            self.session.add(CompanySharePortfolioHoldingModel(
                asset_id=share.id,
                company_share_portfolio_id=sub_portfolio_id,
                container_id=sub_portfolio_id,
                start_date=now,
                position_id=pos.id,
            ))
            self.session.commit()

    def find_ticker_sub_portfolio_id(self, ticker: str) -> Optional[int]:
        """Return the sub-portfolio id for an already-held CompanyShare ticker, or None."""
        from src.infrastructure.models.finance.financial_assets.company_share import CompanyShareModel
        from src.infrastructure.models.finance.holding.company_share_portfolio_holding import (
            CompanySharePortfolioHoldingModel,
        )
        share = self.session.query(CompanyShareModel).filter_by(symbol=ticker).first()
        if not share:
            return None
        holding = self.session.query(CompanySharePortfolioHoldingModel).filter_by(asset_id=share.id).first()
        return holding.company_share_portfolio_id if holding else None