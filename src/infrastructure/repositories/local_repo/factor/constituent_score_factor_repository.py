import logging
from typing import Optional, List
from sqlalchemy.orm import Session

from src.domain.entities.factor.constituent_score_factor import ConstituentScoreFactor
from src.domain.ports.factor.constituent_score_factor_port import ConstituentScoreFactorPort
from src.infrastructure.repositories.mappers.factor.constituent_score_factor_mapper import ConstituentScoreFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository

logger = logging.getLogger(__name__)


class ConstituentScoreFactorRepository(BaseFactorRepository, ConstituentScoreFactorPort):

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = ConstituentScoreFactorMapper()
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
                group=kwargs.get('group', 'fundamental'),
                subgroup=kwargs.get('subgroup', 'score'),
                frequency=kwargs.get('frequency'),
                factor_type=kwargs.get('factor_type', 'constituent_score_factor'),
            )
            if existing:
                return self._to_entity(existing)

            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group', 'fundamental'),
                subgroup=kwargs.get('subgroup', 'score'),
                frequency=kwargs.get('frequency', '1d'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'calculated'),
                definition=kwargs.get('definition', f'Constituent score factor: {primary_key}'),
            )

            orm_factor = self._to_model(domain_factor)
            self.session.add(orm_factor)
            self.session.commit()
            return self._to_entity(orm_factor)

        except Exception as e:
            logger.error(f"Error in _create_or_get for constituent score factor '{primary_key}': {e}")
            self.session.rollback()
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

    def get_by_id(self, id: int) -> Optional[ConstituentScoreFactor]:
        return self._to_entity(
            self.session.query(self.model_class).filter(self.model_class.id == id).one_or_none()
        )

    def get_by_name(self, name: str) -> Optional[ConstituentScoreFactor]:
        try:
            return self._to_entity(
                self.session.query(self.model_class).filter(self.model_class.name == name).first()
            )
        except Exception as e:
            logger.error(f"Error in get_by_name: {e}")
            return None

    def get_all(self) -> List[ConstituentScoreFactor]:
        try:
            return [self._to_entity(m) for m in self.session.query(self.model_class).all()]
        except Exception as e:
            logger.error(f"Error in get_all: {e}")
            return []

    def get_by_group(self, group: str) -> List[ConstituentScoreFactor]:
        try:
            return [
                self._to_entity(m)
                for m in self.session.query(self.model_class)
                .filter(self.model_class.group == group)
                .all()
            ]
        except Exception as e:
            logger.error(f"Error in get_by_group: {e}")
            return []

    def get_by_subgroup(self, subgroup: str) -> List[ConstituentScoreFactor]:
        try:
            return [
                self._to_entity(m)
                for m in self.session.query(self.model_class)
                .filter(self.model_class.subgroup == subgroup)
                .all()
            ]
        except Exception as e:
            logger.error(f"Error in get_by_subgroup: {e}")
            return []

    def add(self, entity: ConstituentScoreFactor) -> Optional[ConstituentScoreFactor]:
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

    def update(self, entity: ConstituentScoreFactor) -> Optional[ConstituentScoreFactor]:
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
