"""
Local repositories of the backtest run registry (2026-11-18): runs, run <-> portfolio and run <-> ML model links.
"""

import math
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.domain.entities.backtest.backtest_run import BacktestRun
from src.domain.entities.backtest.backtest_run_link import BacktestRunModelLink, BacktestRunPortfolio
from src.domain.ports.backtest.backtest_run_port import (
    BacktestRunModelPort,
    BacktestRunPortfolioPort,
    BacktestRunPort,
)
from src.infrastructure.models.backtest.backtest_run import (
    BacktestRunModel,
    BacktestRunModelLinkModel,
    BacktestRunPortfolioModel,
)
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.backtest.backtest_run_mapper import (
    BacktestRunMapper,
    BacktestRunModelLinkMapper,
    BacktestRunPortfolioMapper,
)


def _finite(value):
    return None if isinstance(value, float) and not math.isfinite(value) else value


class BacktestRunRepository(BaseLocalRepository, BacktestRunPort):

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = BacktestRunMapper()

    @property
    def model_class(self):
        return BacktestRunModel

    @property
    def entity_class(self):
        return BacktestRun

    def _to_entity(self, orm_obj) -> Optional[BacktestRun]:
        return self.mapper.to_domain(orm_obj)

    def _to_model(self, entity: BacktestRun) -> BacktestRunModel:
        return self.mapper.to_orm(entity)

    def _create_or_get(self, run_uid: str, **kwargs) -> Optional[BacktestRun]:
        existing = self.get_by_uid(run_uid)
        return existing or self.add(BacktestRun(run_uid=run_uid, **kwargs))

    def add(self, entity: BacktestRun) -> Optional[BacktestRun]:
        entity.starting_capital = _finite(entity.starting_capital)
        orm = self._to_model(entity)
        self.session.add(orm)
        self.session.commit()
        entity.id = orm.id
        return self._to_entity(orm)

    def update(self, entity: BacktestRun) -> Optional[BacktestRun]:
        orm = self.session.get(BacktestRunModel, entity.id)
        if orm is None:
            return None
        self.mapper.apply(entity, orm)
        self.session.commit()
        return self._to_entity(orm)

    def get_by_id(self, id: int) -> Optional[BacktestRun]:
        return self._to_entity(self.session.get(BacktestRunModel, id))

    def get_by_uid(self, run_uid: str) -> Optional[BacktestRun]:
        return self._to_entity(self.session.query(BacktestRunModel).filter(BacktestRunModel.run_uid == run_uid)
                               .one_or_none())

    def find(self, project_name: Optional[str] = None, status: Optional[str] = None,
             run_ids: Optional[List[int]] = None, limit: int = 200) -> List[BacktestRun]:
        q = self.session.query(BacktestRunModel)
        if project_name:
            q = q.filter(BacktestRunModel.project_name == project_name)
        if status:
            q = q.filter(BacktestRunModel.status == status)
        if run_ids:
            q = q.filter(BacktestRunModel.id.in_(list(run_ids)))
        return [self._to_entity(m) for m in q.order_by(BacktestRunModel.id.desc()).limit(limit).all()]

    def get_all(self) -> List[BacktestRun]:
        return [self._to_entity(m) for m in self.session.query(BacktestRunModel).order_by(BacktestRunModel.id).all()]

    def delete(self, id: int) -> bool:
        orm = self.session.get(BacktestRunModel, id)
        if orm is None:
            return False
        self.session.delete(orm)
        self.session.commit()
        return True


class BacktestRunPortfolioRepository(BaseLocalRepository, BacktestRunPortfolioPort):

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = BacktestRunPortfolioMapper()

    @property
    def model_class(self):
        return BacktestRunPortfolioModel

    @property
    def entity_class(self):
        return BacktestRunPortfolio

    def _to_entity(self, orm_obj):
        return self.mapper.to_domain(orm_obj)

    def _to_model(self, entity):
        return self.mapper.to_orm(entity)

    def _create_or_get(self, run_id: int, portfolio_id: int, role: str = "main",
                       label: Optional[str] = None) -> Optional[BacktestRunPortfolio]:
        """A portfolio belongs to ONE run: registering it under another run raises."""
        existing = self.get_by_portfolio(portfolio_id)
        if existing is not None:
            if existing.run_id != run_id:
                raise ValueError(f"portfolio {portfolio_id} already belongs to run {existing.run_id}")
            return existing
        orm = self._to_model(BacktestRunPortfolio(run_id=run_id, portfolio_id=portfolio_id, role=role, label=label))
        self.session.add(orm)
        self.session.commit()
        return self._to_entity(orm)

    def get_by_run(self, run_id: int) -> List[BacktestRunPortfolio]:
        return [self._to_entity(m) for m in self.session.query(BacktestRunPortfolioModel)
                .filter(BacktestRunPortfolioModel.run_id == run_id).order_by(BacktestRunPortfolioModel.id).all()]

    def get_by_portfolio(self, portfolio_id: int) -> Optional[BacktestRunPortfolio]:
        return self._to_entity(self.session.query(BacktestRunPortfolioModel)
                               .filter(BacktestRunPortfolioModel.portfolio_id == portfolio_id).one_or_none())

    def sub_portfolio_ids(self, portfolio_id: int) -> List[int]:
        """Portfolios held by ``portfolio_id`` through *PortfolioPortfolioHolding rows (the engine's sub-portfolios:
        cash, shares, options ...), recursively."""
        from src.infrastructure.models.finance.holding.holding import HoldingModel
        out, frontier, seen = [], [portfolio_id], {portfolio_id}
        while frontier:
            rows = (self.session.query(HoldingModel.asset_id, HoldingModel.holding_type)
                    .filter(HoldingModel.container_id.in_(frontier)).all())
            frontier = []
            for asset_id, holding_type in rows:
                if holding_type and "PortfolioPortfolioHolding" in holding_type and asset_id not in seen:
                    seen.add(asset_id)
                    out.append(int(asset_id))
                    frontier.append(asset_id)
        return out


class BacktestRunModelLinkRepository(BaseLocalRepository, BacktestRunModelPort):

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = BacktestRunModelLinkMapper()

    @property
    def model_class(self):
        return BacktestRunModelLinkModel

    @property
    def entity_class(self):
        return BacktestRunModelLink

    def _to_entity(self, orm_obj):
        return self.mapper.to_domain(orm_obj)

    def _to_model(self, entity):
        return self.mapper.to_orm(entity)

    def _create_or_get(self, run_id: int, ml_model_id: int, role: str = "model",
                       model_artifact_id: Optional[int] = None) -> Optional[BacktestRunModelLink]:
        existing = (self.session.query(BacktestRunModelLinkModel)
                    .filter(BacktestRunModelLinkModel.run_id == run_id,
                            BacktestRunModelLinkModel.ml_model_id == ml_model_id,
                            BacktestRunModelLinkModel.role == role).one_or_none())
        if existing is not None:
            if model_artifact_id is not None and existing.model_artifact_id != model_artifact_id:
                existing.model_artifact_id = model_artifact_id
                self.session.commit()
            return self._to_entity(existing)
        orm = self._to_model(BacktestRunModelLink(run_id=run_id, ml_model_id=ml_model_id, role=role,
                                                  model_artifact_id=model_artifact_id))
        self.session.add(orm)
        self.session.commit()
        return self._to_entity(orm)

    def get_by_run(self, run_id: int) -> List[BacktestRunModelLink]:
        return self.models_by_run([run_id]).get(run_id, [])

    def get_by_model(self, ml_model_id: int) -> List[BacktestRunModelLink]:
        return [self._to_entity(m) for m in self.session.query(BacktestRunModelLinkModel)
                .filter(BacktestRunModelLinkModel.ml_model_id == ml_model_id)
                .order_by(BacktestRunModelLinkModel.run_id.desc()).all()]

    def models_by_run(self, run_ids: List[int]) -> Dict[int, List[BacktestRunModelLink]]:
        out: Dict[int, List[BacktestRunModelLink]] = {rid: [] for rid in run_ids}
        if not run_ids:
            return out
        for m in (self.session.query(BacktestRunModelLinkModel)
                  .filter(BacktestRunModelLinkModel.run_id.in_(list(run_ids)))
                  .order_by(BacktestRunModelLinkModel.id).all()):
            out.setdefault(m.run_id, []).append(self._to_entity(m))
        return out
