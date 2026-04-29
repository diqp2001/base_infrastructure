from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date
from src.infrastructure.models.finance.portfolio.portfolio_company_share import CompanySharePortfolioModel
from src.domain.entities.finance.portfolio.company_share_portfolio import CompanySharePortfolio
from src.infrastructure.repositories.mappers.finance.portfolio.portfolio_company_share_mapper import CompanySharePortfolioMapper
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
    def _create_or_get(self, name: str, **kwargs) -> Optional[CompanySharePortfolio]:

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