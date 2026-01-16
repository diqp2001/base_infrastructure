# Factor Local Repository
# Mirrors src/infrastructure/models/factor/factor.py

from typing import Optional, List
from sqlalchemy.orm import Session

from infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.domain.entities.factor.factor import Factor
from src.infrastructure.models.factor.factor import Factor as FactorModel
from src.domain.ports.factor.factor_port import FactorPort


class FactorRepository(BaseFactorRepository, FactorPort):

    def __init__(self, session: Session):
        super().__init__(session)

    # ----------------------------
    # Required by BaseLocalRepository
    # ----------------------------

    @property
    def model_class(self):
        return FactorModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Factor."""
        return Factor

    def _to_entity(self, model: FactorModel) -> Optional[Factor]:
        if not model:
            return None

        return Factor(
            id=model.id,
            name=model.name,
            group=model.group,
            subgroup=model.subgroup
        )

    def _to_model(self, entity: Factor) -> FactorModel:
        return FactorModel(
            id=entity.id,
            name=entity.name,
            group=entity.group,
            subgroup=entity.subgroup
        )

    def _create_or_get(self, name: str, group: str, subgroup: str) -> Factor:
        existing = self.session.query(FactorModel).filter(
            FactorModel.name == name,
            FactorModel.group == group,
            FactorModel.subgroup == subgroup
        ).first()

        if existing:
            return self._to_entity(existing)

        entity = Factor(
            id=self._get_next_available_id(),
            name=name,
            group=group,
            subgroup=subgroup
        )

        return self.create(entity)

    # ----------------------------
    # Required by FactorPort
    # ----------------------------

    def get_by_id(self, factor_id: int) -> Optional[Factor]:
        model = self.session.query(FactorModel).filter(
            FactorModel.id == factor_id
        ).first()
        return self._to_entity(model)

    def get_by_name(self, name: str) -> Optional[Factor]:
        model = self.session.query(FactorModel).filter(
            FactorModel.name == name
        ).first()
        return self._to_entity(model)

    def get_by_group(self, group: str) -> List[Factor]:
        models = self.session.query(FactorModel).filter(
            FactorModel.group == group
        ).all()
        return [self._to_entity(m) for m in models]

    def get_by_subgroup(self, subgroup: str) -> List[Factor]:
        models = self.session.query(FactorModel).filter(
            FactorModel.subgroup == subgroup
        ).all()
        return [self._to_entity(m) for m in models]
