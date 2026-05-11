from sqlalchemy.orm import Session
from typing import Optional, List

from src.domain.entities.finance.holding.company_share_portfolio_option_portfolio_holding import CompanySharePortfolioOptionPortfolioHolding
from src.domain.ports.finance.holding.company_share_portfolio_option_portfolio_holding_port import CompanySharePortfolioOptionPortfolioHoldingPort
from src.infrastructure.repositories.mappers.finance.holding.company_share_portfolio_option_portfolio_holding_mapper import CompanySharePortfolioOptionPortfolioHoldingMapper


class CompanySharePortfolioOptionPortfolioHoldingRepository(CompanySharePortfolioOptionPortfolioHoldingPort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = CompanySharePortfolioOptionPortfolioHoldingMapper()

    @property
    def entity_class(self):
        return self.mapper.get_entity()

    @property
    def model_class(self):
        return self.mapper.model_class

    # -------------------------
    # CREATE OR GET
    # -------------------------
    def _create_or_get(self, portfolio_id: int, asset_id: int, **kwargs) -> Optional[CompanySharePortfolioOptionPortfolioHolding]:

        try:
            existing = self.get_by_portfolio_and_asset(portfolio_id, asset_id)
            if existing:
                return existing

            # In practice, you'd need to create the entity with proper relationships
            # This is a simplified example
            entity = CompanySharePortfolioOptionPortfolioHolding(
                id=None,
                asset=None,  # Would resolve CompanySharePortfolioOption by asset_id
                portfolio=None,  # Would resolve CompanySharePortfolioOptionPortfolio by portfolio_id
                position=None,  # Would create/resolve Position
                start_date=kwargs.get("start_date"),
                end_date=kwargs.get("end_date"),
            )

            orm_obj = self.mapper.to_orm(entity)

            self.session.add(orm_obj)
            self.session.commit()

            return self.mapper.to_domain(orm_obj)

        except Exception as e:
            print(f"Error creating company share portfolio option portfolio holding: {e}")
            return None

    # -------------------------
    # STANDARD METHODS
    # -------------------------
    def get_by_portfolio_and_asset(self, portfolio_id: int, asset_id: int) -> Optional[CompanySharePortfolioOptionPortfolioHolding]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.company_share_portfolio_option_portfolio_id == portfolio_id)\
            .filter(self.model_class.company_share_portfolio_option_id == asset_id)\
            .one_or_none()
        return self.mapper.to_domain(obj)

    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionPortfolioHolding]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == id)\
            .one_or_none()
        return self.mapper.to_domain(obj)

    def get_by_portfolio_id(self, portfolio_id: int) -> List[CompanySharePortfolioOptionPortfolioHolding]:
        objs = self.session.query(self.model_class)\
            .filter(self.model_class.company_share_portfolio_option_portfolio_id == portfolio_id)\
            .all()
        return [self.mapper.to_domain(o) for o in objs]

    def get_all(self) -> List[CompanySharePortfolioOptionPortfolioHolding]:
        objs = self.session.query(self.model_class).all()
        return [self.mapper.to_domain(o) for o in objs]

    def add(self, entity: CompanySharePortfolioOptionPortfolioHolding) -> Optional[CompanySharePortfolioOptionPortfolioHolding]:
        obj = self.mapper.to_orm(entity)
        self.session.add(obj)
        self.session.commit()
        return self.mapper.to_domain(obj)

    def update(self, entity: CompanySharePortfolioOptionPortfolioHolding) -> Optional[CompanySharePortfolioOptionPortfolioHolding]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == entity.id)\
            .one_or_none()

        if not obj:
            return None

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