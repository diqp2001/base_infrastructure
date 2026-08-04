from typing import Optional
from src.domain.entities.entity import Entity


class BacktestFactorBacktest(Entity):
    """Association between a BacktestFactor and a Backtest (join table domain entity)."""

    def __init__(self, id: Optional[int], backtest_id: int, backtest_factor_id: int):
        super().__init__(id)
        self.backtest_id = backtest_id
        self.backtest_factor_id = backtest_factor_id

    def __repr__(self):
        return (
            f"BacktestFactorBacktest(id={self.id}, "
            f"backtest_id={self.backtest_id}, backtest_factor_id={self.backtest_factor_id})"
        )
