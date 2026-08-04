from typing import Optional
from src.domain.entities.backtest.model import Model
from src.infrastructure.models.backtest.model import ModelModel


class ModelMapper:

    @staticmethod
    def to_domain(orm_obj: ModelModel) -> Optional[Model]:
        if not orm_obj:
            return None
        return Model(id=orm_obj.id, name=orm_obj.name)

    @staticmethod
    def to_orm(domain_obj: Model) -> ModelModel:
        return ModelModel(name=domain_obj.name)
