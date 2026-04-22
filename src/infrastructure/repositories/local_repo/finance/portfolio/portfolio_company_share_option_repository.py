from sqlalchemy.orm import Session
from typing import Optional, List

from src.domain.entities.finance.portfolio.portfolio_company_share_option import PortfolioCompanyShareOption
from src.domain.ports.finance.portfolio.portfolio_company_share_option_port import PortfolioCompanyShareOptionPort
from src.infrastructure.repositories.mappers.finance.portfolio.portfolio_company_share_option_mapper import PortfolioCompanyShareOptionMapper


class PortfolioCompanyShareOptionRepository(PortfolioCompanyShareOptionPort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = PortfolioCompanyShareOptionMapper()

    @property
    def entity_class(self):
        return self.mapper.get_entity()

    @property
    def model_class(self):
        return self.mapper.model_class

    # -------------------------
    # CREATE OR GET
    # -------------------------
    def _create_or_get(self, name: str, **kwargs) -> Optional[PortfolioCompanyShareOption]:

        try:
            existing = self.get_by_name(name)
            if existing:
                return existing

            entity = PortfolioCompanyShareOption(
                id=None,
                name=name,
                start_date=kwargs.get("start_date"),
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
    def get_by_name(self, name: str) -> Optional[PortfolioCompanyShareOption]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.name == name)\
            .one_or_none()
        return self.mapper.to_domain(obj)

    def get_by_id(self, id: int) -> Optional[PortfolioCompanyShareOption]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == id)\
            .one_or_none()
        return self.mapper.to_domain(obj)

    def get_all(self) -> List[PortfolioCompanyShareOption]:
        objs = self.session.query(self.model_class).all()
        return [self.mapper.to_domain(o) for o in objs]

    def add(self, entity: PortfolioCompanyShareOption) -> Optional[PortfolioCompanyShareOption]:
        obj = self.mapper.to_orm(entity)
        self.session.add(obj)
        self.session.commit()
        return self.mapper.to_domain(obj)

    def update(self, entity: PortfolioCompanyShareOption) -> Optional[PortfolioCompanyShareOption]:
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