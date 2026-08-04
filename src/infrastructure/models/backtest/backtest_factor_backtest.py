from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class BacktestFactorBacktestModel(Base):
    __tablename__ = 'backtest_factor_backtests'

    id = Column(Integer, primary_key=True, autoincrement=True)
    backtest_id = Column(Integer, ForeignKey('backtests.id'), nullable=False)
    backtest_factor_id = Column(Integer, ForeignKey('factors.id'), nullable=False)

    backtest = relationship(
        "src.infrastructure.models.backtest.backtest.BacktestModel",
        back_populates="backtest_factor_backtests",
    )
    backtest_factor = relationship("src.infrastructure.models.factor.factor.FactorModel")

    def __repr__(self):
        return (
            f"<BacktestFactorBacktest(id={self.id}, "
            f"backtest_id={self.backtest_id}, backtest_factor_id={self.backtest_factor_id})>"
        )
