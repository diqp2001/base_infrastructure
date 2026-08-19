import logging
from typing import Optional
from sqlalchemy.orm import Session

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_atm_implied_vol_factor import CompanyShareATMImpliedVolFactor
from src.domain.ports.factor.finance.financial_assets.share_factor.company_share.company_share_atm_implied_vol_factor_port import CompanyShareATMImpliedVolFactorPort
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.share.company_share.company_share_atm_implied_vol_factor_mapper import CompanyShareATMImpliedVolFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository

logger = logging.getLogger(__name__)


class CompanyShareATMImpliedVolFactorRepository(BaseFactorRepository, CompanyShareATMImpliedVolFactorPort):

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = CompanyShareATMImpliedVolFactorMapper()
        self.mapper_value = FactorValueMapper()

    @property
    def entity_class(self):
        return self.get_factor_entity()

    @property
    def model_class(self):
        return self.mapper.model_class

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

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs):
        try:
            existing = self.get_by_all(
                name=primary_key,
                group=kwargs.get('group', 'volatility'),
                subgroup=kwargs.get('subgroup', 'implied'),
                frequency=kwargs.get('frequency'),
                factor_type=kwargs.get('factor_type', 'company_share_atm_implied_vol_factor'),
            )
            if existing:
                return self._to_entity(existing)

            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group', 'volatility'),
                subgroup=kwargs.get('subgroup', 'implied'),
                frequency=kwargs.get('frequency', '1d'),
                data_type=kwargs.get('data_type', 'decimal'),
                source=kwargs.get('source', 'ibkr'),
                definition=kwargs.get('definition', f'ATM implied volatility: {primary_key}'),
            )

            orm_factor = self._to_model(domain_factor)
            self.session.add(orm_factor)
            self.session.commit()
            return self._to_entity(orm_factor)

        except Exception as e:
            logger.error(f"Error in _create_or_get for ATM implied vol factor '{primary_key}': {e}")
            return None

    def get_by_all(self, name, group, factor_type=None, subgroup=None, frequency=None, data_type=None, source=None):
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
            logger.error(f"Error in get_by_all: {e}")
            return None

    def get_by_id(self, id: int):
        return self._to_entity(
            self.session.query(self.model_class).filter(self.model_class.id == id).one_or_none()
        )

    def get_by_name(self, name: str) -> Optional[CompanyShareATMImpliedVolFactor]:
        try:
            return self._to_entity(
                self.session.query(self.model_class).filter(self.model_class.name == name).first()
            )
        except Exception as e:
            logger.error(f"Error in get_by_name: {e}")
            return None

    def get_all(self):
        try:
            return [self._to_entity(m) for m in self.session.query(self.model_class).all()]
        except Exception as e:
            logger.error(f"Error in get_all: {e}")
            return []

    def get_by_group(self, group: str):
        try:
            return [self._to_entity(m) for m in self.session.query(self.model_class).filter(
                self.model_class.group == group).all()]
        except Exception as e:
            logger.error(f"Error in get_by_group: {e}")
            return []

    def get_by_subgroup(self, subgroup: str):
        try:
            return [self._to_entity(m) for m in self.session.query(self.model_class).filter(
                self.model_class.subgroup == subgroup).all()]
        except Exception as e:
            logger.error(f"Error in get_by_subgroup: {e}")
            return []

    def add(self, entity: CompanyShareATMImpliedVolFactor) -> Optional[CompanyShareATMImpliedVolFactor]:
        try:
            model = self._to_model(entity)
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)
            return self._to_entity(model)
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error in add: {e}")
            return None

    def update(self, entity: CompanyShareATMImpliedVolFactor) -> Optional[CompanyShareATMImpliedVolFactor]:
        try:
            model = self._to_model(entity)
            updated = self.session.merge(model)
            self.session.commit()
            return self._to_entity(updated)
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error in update: {e}")
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
            logger.error(f"Error in delete: {e}")
            return False
