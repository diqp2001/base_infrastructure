from sqlalchemy import Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class BacktestModel(Base):
    __tablename__ = 'backtests'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    creation_date = Column(Date, nullable=False)

    model = relationship("src.infrastructure.models.backtest.model.ModelModel")
    backtest_factor_backtests = relationship(
        "src.infrastructure.models.backtest.backtest_factor_backtest.BacktestFactorBacktestModel",
        back_populates="backtest",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Backtest(id={self.id}, name='{self.name}', model_id={self.model_id})>"
