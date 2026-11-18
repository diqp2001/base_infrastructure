"""
Associations of a BacktestRun (generic research / backtest registry, 2026-11-18).

BacktestRunPortfolio  a portfolio the run created (main book, sub-portfolios, benchmark, variant sleeves ...): one
                      run can own several portfolios; a portfolio belongs to one run.
BacktestRunModelLink      an ML model (ml_models) the run used, with its role ('traded', a variant label 'A' / 'B',
                      'scoring' ...) and the artifact when known. One model can be used by many runs, on any
                      universe.
"""

from __future__ import annotations

from typing import Optional

from src.domain.entities.entity import Entity


class BacktestRunPortfolio(Entity):

    def __init__(self, run_id: int, portfolio_id: int, role: str = "main", id: Optional[int] = None,
                 label: Optional[str] = None):
        super().__init__(id)
        self.run_id = run_id
        self.portfolio_id = portfolio_id
        self.role = role                     # main | sub | benchmark | variant | sleeve
        self.label = label

    def to_dict(self):
        return {"id": self.id, "run_id": self.run_id, "portfolio_id": self.portfolio_id, "role": self.role,
                "label": self.label}

    def __repr__(self) -> str:
        return f"<BacktestRunPortfolio(run={self.run_id}, portfolio={self.portfolio_id}, {self.role})>"


class BacktestRunModelLink(Entity):

    def __init__(self, run_id: int, ml_model_id: int, role: str = "model", id: Optional[int] = None,
                 model_artifact_id: Optional[int] = None):
        super().__init__(id)
        self.run_id = run_id
        self.ml_model_id = ml_model_id
        self.role = role
        self.model_artifact_id = model_artifact_id

    def to_dict(self):
        return {"id": self.id, "run_id": self.run_id, "ml_model_id": self.ml_model_id, "role": self.role,
                "model_artifact_id": self.model_artifact_id}

    def __repr__(self) -> str:
        return f"<BacktestRunModelLink(run={self.run_id}, model={self.ml_model_id}, {self.role})>"
