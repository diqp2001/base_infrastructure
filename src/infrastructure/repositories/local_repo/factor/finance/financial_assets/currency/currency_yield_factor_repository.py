"""
Local repository for CurrencyYieldFactor operations.

Creates a FactorDependency linking CurrencyYieldFactor → BondFutureAnnualizedYieldFactor
with dependency_name='rate'.  At resolution time, _handle_missing_dependency delegates
to get_related_entities(), which maps the currency ISO code to the benchmark bond future
(USD→SR3, CAD→CORRA) so the resolution service can recurse into it.
"""

from datetime import timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from src.domain.entities.factor.factor_dependency import FactorDependency
from src.domain.entities.factor.finance.financial_assets.currency.currency_yield_factor import CurrencyYieldFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_annualized_yield_factor import BondFutureAnnualizedYieldFactor
from src.domain.ports.factor.finance.financial_assets.currency.currency_yield_factor_port import CurrencyYieldFactorPort
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.currency.currency_yield_factor_mapper import CurrencyYieldFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper


class CurrencyYieldFactorRepository(BaseFactorRepository, CurrencyYieldFactorPort):
    """Local repository for CurrencyYieldFactor entities."""

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = CurrencyYieldFactorMapper()
        self.mapper_value = FactorValueMapper()

    @property
    def entity_class(self):
        return self.get_factor_entity()

    @property
    def model_class(self):
        return self.mapper.model_class

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs):
        """Get or create a CurrencyYieldFactor and wire its benchmark dependency."""
        try:
            existing = self.get_by_all(
                frequency=kwargs.get('frequency'),
                name=primary_key,
                group=kwargs.get('group', 'fundamental'),
                factor_type=kwargs.get('factor_type', 'currency_yield_factor'),
            )
            if existing:
                factor_entity = self._to_entity(existing)
                self._ensure_benchmark_dependency(factor_entity)
                return factor_entity

            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group') or 'fundamental',
                subgroup=kwargs.get('subgroup') or 'yield',
                frequency=kwargs.get('frequency') or '1d',
                data_type=kwargs.get('data_type') or 'decimal',
                source=kwargs.get('source') or 'calculated',
                definition=kwargs.get('definition') or f'Risk-free yield for currency: {primary_key}',
            )

            orm_factor = self._to_model(domain_factor)
            self.session.add(orm_factor)
            self.session.commit()

            factor_entity = self._to_entity(orm_factor)
            self._ensure_benchmark_dependency(factor_entity)
            return factor_entity

        except Exception as e:
            print(f"Error in _create_or_get CurrencyYieldFactor '{primary_key}': {e}")
            return None

    def _ensure_benchmark_dependency(self, factor_entity: CurrencyYieldFactor) -> None:
        """Create a FactorDependency → BondFutureAnnualizedYieldFactor if absent."""
        if not self.factory or not factor_entity or not factor_entity.id:
            return
        try:
            annualized_yield_repo = self.factory.get_local_repository('BondFutureAnnualizedYieldFactor')
            if not annualized_yield_repo:
                return
            dep_factor = annualized_yield_repo._create_or_get(
                BondFutureAnnualizedYieldFactor,
                primary_key='Annualized Yield',
                frequency=factor_entity.frequency,
            )
            if not dep_factor:
                return

            dep_dep_repo = self.factory.get_local_repository(FactorDependency)
            if dep_dep_repo:
                dep_dep_repo._create_or_get(
                    independent_factor=dep_factor,
                    dependent_factor=factor_entity,
                    lag=timedelta(days=1),
                    dependency_name='rate',
                )
        except Exception as e:
            print(f"Error ensuring benchmark dependency for CurrencyYieldFactor: {e}")

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
            print(f"Error retrieving CurrencyYieldFactor by all attributes: {e}")
            return None

    def get_by_id(self, id: int):
        return self._to_entity(
            self.session.query(self.model_class)
            .filter(self.model_class.id == id)
            .one_or_none()
        )

    def get_by_name(self, name: str):
        orm = (
            self.session.query(self.model_class)
            .filter(self.model_class.name == name)
            .first()
        )
        return self._to_entity(orm) if orm else None

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
