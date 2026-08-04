from typing import Optional
from src.domain.entities.backtest.backtest import Backtest
from src.infrastructure.models.backtest.backtest import BacktestModel


class BacktestMapper:

    @staticmethod
    def to_domain(orm_obj: BacktestModel) -> Optional[Backtest]:
        if not orm_obj:
            return None
        return Backtest(
            id=orm_obj.id,
            name=orm_obj.name,
            model_id=orm_obj.model_id,
            creation_date=orm_obj.creation_date,
        )

    @staticmethod
    def to_orm(domain_obj: Backtest) -> BacktestModel:
        return BacktestModel(
            name=domain_obj.name,
            model_id=domain_obj.model_id,
            creation_date=domain_obj.creation_date,
        )
