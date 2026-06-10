from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date
from src.domain.entities.finance.portfolio.company_share_portfolio_option_portfolio import CompanySharePortfolioOptionPortfolio
from src.domain.ports.finance.portfolio.company_share_portfolio_option_portfolio_port import CompanySharePortfolioOptionPortfolioPort
from src.infrastructure.repositories.mappers.finance.portfolio.company_share_portfolio_option_portfolio_mapper import CompanySharePortfolioOptionPortfolioMapper


class CompanySharePortfolioOptionPortfolioRepository(CompanySharePortfolioOptionPortfolioPort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = CompanySharePortfolioOptionPortfolioMapper()

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
    
    def _create_or_get(self, name: str, **kwargs) -> Optional[CompanySharePortfolioOptionPortfolio]:

        try:
            existing = self.get_by_name(name)
            if existing:
                return existing

            entity = CompanySharePortfolioOptionPortfolio(
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
            print(f"Error creating company share portfolio option portfolio {name}: {e}")
            return None

    # -------------------------
    # STANDARD METHODS
    # -------------------------
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionPortfolio]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.name == name)\
            .one_or_none()
        return self.mapper.to_domain(obj) if obj else None

    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionPortfolio]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == id)\
            .one_or_none()
        return self.mapper.to_domain(obj)

    def get_all(self) -> List[CompanySharePortfolioOptionPortfolio]:
        objs = self.session.query(self.model_class).all()
        return [self.mapper.to_domain(o) for o in objs]

    def add(self, entity: CompanySharePortfolioOptionPortfolio) -> Optional[CompanySharePortfolioOptionPortfolio]:
        obj = self.mapper.to_orm(entity)
        self.session.add(obj)
        self.session.commit()
        return self.mapper.to_domain(obj)

    def update(self, entity: CompanySharePortfolioOptionPortfolio) -> Optional[CompanySharePortfolioOptionPortfolio]:
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
        """Return all holdings whose container_id matches this sub-portfolio."""
        try:
            from src.infrastructure.repositories.local_repo.finance.holding.holding_repository import HoldingRepository
            holding_repo = HoldingRepository(self.session, self.factory)
            return holding_repo.get_by_container_id(portfolio_id)
        except Exception as e:
            print(f"Error retrieving holdings for CompanySharePortfolioOptionPortfolio {portfolio_id}: {e}")
            return []