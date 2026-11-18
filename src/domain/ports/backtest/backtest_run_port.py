"""Ports of the backtest run registry (2026-11-18): runs, their portfolios and models."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from src.domain.entities.backtest.backtest_run import BacktestRun
from src.domain.entities.backtest.backtest_run_link import BacktestRunModelLink, BacktestRunPortfolio


class BacktestRunPort(ABC):

    @abstractmethod
    def add(self, entity: BacktestRun) -> Optional[BacktestRun]: ...

    @abstractmethod
    def update(self, entity: BacktestRun) -> Optional[BacktestRun]: ...

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[BacktestRun]: ...

    @abstractmethod
    def get_by_uid(self, run_uid: str) -> Optional[BacktestRun]: ...

    @abstractmethod
    def find(self, project_name: Optional[str] = None, status: Optional[str] = None,
             run_ids: Optional[List[int]] = None, limit: int = 200) -> List[BacktestRun]: ...

    @abstractmethod
    def get_all(self) -> List[BacktestRun]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...


class BacktestRunPortfolioPort(ABC):

    @abstractmethod
    def _create_or_get(self, run_id: int, portfolio_id: int, role: str = "main",
                       label: Optional[str] = None) -> Optional[BacktestRunPortfolio]: ...

    @abstractmethod
    def get_by_run(self, run_id: int) -> List[BacktestRunPortfolio]: ...

    @abstractmethod
    def get_by_portfolio(self, portfolio_id: int) -> Optional[BacktestRunPortfolio]: ...


class BacktestRunModelPort(ABC):

    @abstractmethod
    def _create_or_get(self, run_id: int, ml_model_id: int, role: str = "model",
                       model_artifact_id: Optional[int] = None) -> Optional[BacktestRunModelLink]: ...

    @abstractmethod
    def get_by_run(self, run_id: int) -> List[BacktestRunModelLink]: ...

    @abstractmethod
    def get_by_model(self, ml_model_id: int) -> List[BacktestRunModelLink]: ...

    @abstractmethod
    def models_by_run(self, run_ids: List[int]) -> Dict[int, List[BacktestRunModelLink]]: ...
