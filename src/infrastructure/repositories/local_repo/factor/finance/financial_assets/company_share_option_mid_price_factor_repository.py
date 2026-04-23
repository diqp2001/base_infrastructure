"""
src/infrastructure/repositories/local_repo/factor/finance/financial_assets/company_share_option_mid_price_factor_repository.py

Local repository for CompanyShareOptionMidPriceFactor operations.
"""

from sqlalchemy.orm import Session
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_mid_price_factor import CompanyShareOptionMidPriceFactor
from src.domain.ports.factor.company_share_option_mid_price_factor_port import CompanyShareOptionMidPriceFactorPort
from src.infrastructure.repositories.mappers.factor.company_share_option_mid_price_factor_mapper import CompanyShareOptionMidPriceFactorMapper


class CompanyShareOptionMidPriceFactorRepository(CompanyShareOptionMidPriceFactorPort):
    """Local repository for CompanyShareOptionMidPriceFactor operations."""

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = CompanyShareOptionMidPriceFactorMapper()

    @property
    def entity_class(self):
        return self.mapper.get_entity()

    @property
    def model_class(self):
        return self.mapper.model_class

    def _create_or_get(self, name: str, **kwargs) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Create new factor or get existing one."""
        try:
            existing = self.get_by_name(name)
            if existing:
                return existing

            entity = CompanyShareOptionMidPriceFactor(
                name=name,
                group=kwargs.get("group", "price"),
                subgroup=kwargs.get("subgroup", "mid_price_true"),
                frequency=kwargs.get("frequency"),
                data_type=kwargs.get("data_type", "decimal"),
                source=kwargs.get("source", "multiple"),
                definition=kwargs.get("definition", "True mid price calculated from multiple data sources with outlier filtering"),
                outlier_threshold=kwargs.get("outlier_threshold", 2.0),
                min_sources=kwargs.get("min_sources", 2),
            )

            orm_obj = self.mapper.to_orm(entity)
            self.session.add(orm_obj)
            self.session.commit()

            return self.mapper.to_domain(orm_obj)

        except Exception as e:
            print(f"Error creating/getting CompanyShareOptionMidPriceFactor {name}: {e}")
            self.session.rollback()
            return None

    def get_by_name(self, name: str) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Get factor by name."""
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.name == name)\
            .one_or_none()
        return self.mapper.to_domain(obj)

    def get_by_id(self, id: int) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Get factor by ID."""
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == id)\
            .one_or_none()
        return self.mapper.to_domain(obj)

    def get_all(self) -> List[CompanyShareOptionMidPriceFactor]:
        """Get all factors."""
        objs = self.session.query(self.model_class).all()
        return [self.mapper.to_domain(o) for o in objs]

    def add(self, entity: CompanyShareOptionMidPriceFactor) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Add new factor."""
        obj = self.mapper.to_orm(entity)
        self.session.add(obj)
        self.session.commit()
        return self.mapper.to_domain(obj)

    def update(self, entity: CompanyShareOptionMidPriceFactor) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Update existing factor."""
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == entity.id)\
            .one_or_none()

        if not obj:
            return None

        obj.name = entity.name
        obj.group = entity.group
        obj.subgroup = entity.subgroup
        obj.frequency = entity.frequency
        obj.data_type = entity.data_type
        obj.source = entity.source
        obj.definition = entity.definition

        self.session.commit()
        return self.mapper.to_domain(obj)

    def delete(self, id: int) -> bool:
        """Delete factor by ID."""
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == id)\
            .one_or_none()

        if not obj:
            return False

        self.session.delete(obj)
        self.session.commit()
        return True