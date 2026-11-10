"""
Repository class for ETFShareFactor entities - mirrors CompanyShareFactorRepository (raw IBKR series of the ETF share:
name = bar field, subgroup = whatToShow, frequency = bar size).
"""
import logging
from sqlalchemy.orm import Session
from typing import Optional

from src.infrastructure.repositories.mappers.factor.finance.financial_assets.share.etf_share.etf_share_factor_mapper import ETFShareFactorMapper
from src.infrastructure.models.factor.factor import FactorModel
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_factor import ETFShareFactor
from src.domain.ports.factor.finance.financial_assets.share_factor.etf_share.etf_share_factor_port import ETFShareFactorPort
from .....base_factor_repository import BaseFactorRepository

logger = logging.getLogger(__name__)


class ETFShareFactorRepository(BaseFactorRepository, ETFShareFactorPort):
    """Repository for ETFShareFactor entities with CRUD operations."""

    FACTOR_TYPE = 'etf_share_factor'

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = self._mapper()

    def _mapper(self):
        return ETFShareFactorMapper()

    @property
    def model_class(self):
        return self.mapper.get_factor_model()

    @property
    def entity_class(self):
        return self.mapper.get_factor_entity()

    def get_factor_model(self):
        return self.mapper.get_factor_model()

    def get_factor_entity(self):
        return self.mapper.get_factor_entity()

    def _to_entity(self, infra_factor) -> Optional[ETFShareFactor]:
        if not infra_factor:
            return None
        return self.mapper.to_domain(infra_factor)

    def _to_model(self, entity: ETFShareFactor) -> FactorModel:
        if not entity:
            return None
        return self.mapper.to_orm(entity)

    def _to_domain(self, infra_factor) -> Optional[ETFShareFactor]:
        return self._to_entity(infra_factor)

    def _defaults(self, primary_key: str, kwargs: dict) -> dict:
        """BI-036: a raw IBKR bar field names its series - subgroup = whatToShow; without one, the series read first
        for that field (ETF prices: TRADES)."""
        from src.domain.entities.factor.source_policy import is_raw_bar_field, reading_order
        defaults = {'group': 'price', 'data_type': 'numeric', 'source': 'ibkr'}
        if not kwargs.get('subgroup'):
            source = kwargs.get('source', 'ibkr')
            defaults['subgroup'] = (reading_order("ETFShare", kwargs.get('group', 'price'), primary_key)[0]
                                    if source == 'ibkr' and is_raw_bar_field(primary_key) else 'ohlc')
        return defaults

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs):
        try:
            kwargs = self._normalize_kwargs({**self._defaults(primary_key, kwargs), **kwargs})
            existing = self.get_by_all(name=primary_key, group=kwargs.get('group'), subgroup=kwargs.get('subgroup'),
                                       frequency=kwargs.get('frequency'),
                                       factor_type=kwargs.get('factor_type', self.FACTOR_TYPE))
            if existing:
                return self._to_entity(existing)
            domain_factor = self.get_factor_entity()(
                name=primary_key, group=kwargs.get('group'), subgroup=kwargs.get('subgroup'),
                frequency=kwargs.get('frequency'), data_type=kwargs.get('data_type'), source=kwargs.get('source'),
                definition=kwargs.get('definition', f'{self.mapper.discriminator} factor: {primary_key}'))
            orm_factor = self._to_model(domain_factor)
            self.session.add(orm_factor)
            self.session.commit()
            return self._to_entity(orm_factor)
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error in get_or_create for {self.FACTOR_TYPE} {primary_key}: {e}")
            return None

    def get_by_id(self, entity_id: int) -> Optional[ETFShareFactor]:
        try:
            return self._to_domain(self.session.query(self.model_class).filter(self.model_class.id == entity_id).first())
        except Exception as e:
            logger.error(f"Error retrieving {self.FACTOR_TYPE} by ID {entity_id}: {e}")
            return None

    def get_by_name(self, name: str) -> Optional[ETFShareFactor]:
        try:
            return self._to_domain(self.session.query(self.model_class).filter(self.model_class.name == name).first())
        except Exception as e:
            logger.error(f"Error retrieving {self.FACTOR_TYPE} by name {name}: {e}")
            return None

    def get_all(self) -> list[ETFShareFactor]:
        try:
            return [self._to_domain(f) for f in self.session.query(self.model_class).all()]
        except Exception as e:
            logger.error(f"Error retrieving all {self.FACTOR_TYPE}: {e}")
            return []

    def add(self, entity: ETFShareFactor) -> Optional[ETFShareFactor]:
        try:
            new_factor = self._to_model(entity)
            self.session.add(new_factor)
            self.session.commit()
            self.session.refresh(new_factor)
            return self._to_domain(new_factor)
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding {self.FACTOR_TYPE}: {e}")
            return None

    def get_by_all(self, name: str, group: str, factor_type: Optional[str] = None, subgroup: Optional[str] = None,
                   frequency: Optional[str] = None, data_type: Optional[str] = None, source: Optional[str] = None):
        """Retrieve a factor matching all provided (non-None) fields."""
        try:
            model = self.get_factor_model()
            query = self.session.query(model).filter(model.name == name, model.group == group)
            for column, value in (("factor_type", factor_type), ("subgroup", subgroup), ("frequency", frequency),
                                  ("data_type", data_type), ("source", source)):
                if value is not None:
                    query = query.filter(getattr(model, column) == value)
            return query.first()
        except Exception as e:
            logger.error(f"Error retrieving factor by all attributes: {e}")
            return None

    def get_by_group(self, group: str) -> list[ETFShareFactor]:
        try:
            return [self._to_domain(f) for f in
                    self.session.query(self.model_class).filter(self.model_class.group == group).all()]
        except Exception as e:
            logger.error(f"Error retrieving {self.FACTOR_TYPE} by group {group}: {e}")
            return []

    def get_by_subgroup(self, subgroup: str) -> list[ETFShareFactor]:
        try:
            return [self._to_domain(f) for f in
                    self.session.query(self.model_class).filter(self.model_class.subgroup == subgroup).all()]
        except Exception as e:
            logger.error(f"Error retrieving {self.FACTOR_TYPE} by subgroup {subgroup}: {e}")
            return []

    def update(self, entity: ETFShareFactor) -> Optional[ETFShareFactor]:
        try:
            updated_model = self.session.merge(self._to_model(entity))
            self.session.commit()
            return self._to_domain(updated_model)
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating {self.FACTOR_TYPE}: {e}")
            return None

    def delete(self, entity_id: int) -> bool:
        try:
            factor = self.session.query(self.model_class).filter(self.model_class.id == entity_id).first()
            if factor:
                self.session.delete(factor)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting {self.FACTOR_TYPE} with ID {entity_id}: {e}")
            return False
