from typing import Optional
from src.domain.entities.backtest.universe import Universe
from src.infrastructure.models.backtest.universe import UniverseModel


class UniverseMapper:

    @staticmethod
    def to_domain(orm_obj: UniverseModel) -> Optional[Universe]:
        if not orm_obj:
            return None
        return Universe(
            id=orm_obj.id,
            name=orm_obj.name,
            creation_date=orm_obj.creation_date,
            description=orm_obj.description,
        )

    @staticmethod
    def to_orm(domain_obj: Universe) -> UniverseModel:
        return UniverseModel(
            name=domain_obj.name,
            creation_date=domain_obj.creation_date,
            description=domain_obj.description,
        )
