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