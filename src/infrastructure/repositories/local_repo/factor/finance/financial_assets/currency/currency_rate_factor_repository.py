"""
Local repository for CurrencyRateFactor operations.
"""

from typing import Optional
from sqlalchemy.orm import Session

from src.domain.entities.factor.finance.financial_assets.currency.currency_rate_factor import CurrencyRateFactor
from src.domain.ports.factor.currency_rate_factor_port import CurrencyRateFactorPort
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.currency.currency_rate_factor_mapper import CurrencyRateFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper


class CurrencyRateFactorRepository(BaseFactorRepository, CurrencyRateFactorPort):
    """Local repository for CurrencyRateFactor entities."""

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = CurrencyRateFactorMapper()
        self.mapper_value = FactorValueMapper()

    @property
    def entity_class(self):
        return self.get_factor_entity()

    @property
    def model_class(self):
        return self.mapper.model_class

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs):
        """Get or create a CurrencyRateFactor."""
        try:
            existing = self.get_by_all(
                name=primary_key,
                group=kwargs.get('group', 'price'),
                factor_type=kwargs.get('factor_type', 'currency_rate_factor'),
            )
            if existing:
                return self._to_entity(existing)

            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group', 'price'),
                subgroup=kwargs.get('subgroup', 'mid_price_true'),
                frequency=kwargs.get('frequency', None),
                data_type=kwargs.get('data_type', 'decimal'),
                source=kwargs.get('source', 'multiple'),
                definition=kwargs.get('definition', f'True mid exchange rate: {primary_key}'),
            )

            orm_factor = self._to_model(domain_factor)
            self.session.add(orm_factor)
            self.session.commit()
            return self._to_entity(orm_factor)

        except Exception as e:
            print(f"Error in _create_or_get CurrencyRateFactor '{primary_key}': {e}")
            return None

    def get_by_all(
        self,
        name: str,
        group: str,
        factor_type: Optional[str] = None,
        subgroup: Optional[str] = None,
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
    ):
        """Retrieve a factor matching all provided (non-None) fields."""
        try:
            FactorModel = self.get_factor_model()
            query = self.session.query(FactorModel).filter(
                FactorModel.name == name,
                FactorModel.group == group,
            )
            if factor_type is not None:
                query = query.filter(FactorModel.factor_type == factor_type)
            if subgroup is not None:
                query = query.filter(FactorModel.subgroup == subgroup)
            if frequency is not None:
                query = query.filter(FactorModel.frequency == frequency)
            if data_type is not None:
                query = query.filter(FactorModel.data_type == data_type)
            if source is not None:
                query = query.filter(FactorModel.source == source)
            return query.first()
        except Exception as e:
            print(f"Error retrieving CurrencyRateFactor by all attributes: {e}")
            return None

    def get_by_id(self, id: int):
        return self._to_entity(
            self.session.query(self.model_class)
            .filter(self.model_class.id == id)
            .one_or_none()
        )

    def get_factor_model(self):
        return self.mapper.get_factor_model()

    def get_factor_entity(self):
        return self.mapper.get_factor_entity()

    def get_factor_value_model(self):
        return self.mapper_value.get_factor_value_model()

    def get_factor_value_entity(self):
        return self.mapper_value.get_factor_value_entity()

    def _to_entity(self, infra_obj):
        return self.mapper.to_domain(infra_obj)

    def _to_model(self, entity):
        return self.mapper.to_orm(entity)
