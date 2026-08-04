from typing import Optional
from src.domain.entities.backtest.backtest_factor_backtest import BacktestFactorBacktest
from src.infrastructure.models.backtest.backtest_factor_backtest import BacktestFactorBacktestModel


class BacktestFactorBacktestMapper:

    @staticmethod
    def to_domain(orm_obj: BacktestFactorBacktestModel) -> Optional[BacktestFactorBacktest]:
        if not orm_obj:
            return None
        return BacktestFactorBacktest(
            id=orm_obj.id,
            backtest_id=orm_obj.backtest_id,
            backtest_factor_id=orm_obj.backtest_factor_id,
        )

    @staticmethod
    def to_orm(domain_obj: BacktestFactorBacktest) -> BacktestFactorBacktestModel:
        return BacktestFactorBacktestModel(
            backtest_id=domain_obj.backtest_id,
            backtest_factor_id=domain_obj.backtest_factor_id,
        )
