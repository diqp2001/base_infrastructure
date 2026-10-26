"""
StrategyServices — wires the strategy use cases onto a database (what the Flask routes and the worker use).

``from_database()`` connects to the configured database (SQL Server base_infra by default; new tables are created on
connection). Tests build it on an in-memory SQLite session with ``StrategyServices(session=...)``.
"""

from __future__ import annotations

from typing import Callable, Optional

from src.application.services.strategy.configuration_service import StrategyConfigurationService
from src.application.services.strategy.experiment_service import ExperimentService, JobRunner
from src.application.services.strategy.project_adapters import ProjectRegistry


class StrategyServices:

    def __init__(self, session, database_service=None, registry: Optional[ProjectRegistry] = None,
                 runner: Optional[JobRunner] = None, session_factory: Optional[Callable] = None, **experiment_kwargs):
        from src.infrastructure.repositories.local_repo.ml.model_artifact_repository import ModelArtifactRepository
        from src.infrastructure.repositories.local_repo.strategy.strategy_repositories import (
            StrategyConfigurationRepository,
            StrategyExperimentRepository,
        )
        self.session = session
        self.database_service = database_service
        self.session_factory = session_factory
        self.registry = registry or ProjectRegistry()
        self.configuration_repository = StrategyConfigurationRepository(session)
        self.experiment_repository = StrategyExperimentRepository(session)
        self.configurations = StrategyConfigurationService(self.configuration_repository, self.registry)
        self.experiments = ExperimentService(self.experiment_repository, self.configurations, runner=runner,
                                             artifact_repository=ModelArtifactRepository(session),
                                             **experiment_kwargs)

    def new_experiment_repository(self):
        """A repository on its OWN session (the worker's heartbeat thread must not share the run's session)."""
        from src.infrastructure.repositories.local_repo.strategy.strategy_repositories import (
            StrategyExperimentRepository,
        )
        if self.session_factory is None:
            raise RuntimeError("no session factory: heartbeats need their own database session")
        return StrategyExperimentRepository(self.session_factory())

    @classmethod
    def from_database(cls, db_type: str = "sql_server", **kwargs) -> "StrategyServices":
        from sqlalchemy.orm import sessionmaker

        from src.application.services.database_service.database_service import DatabaseService
        database_service = DatabaseService(db_type)
        database_service.set_ext_db()
        engine = database_service.session.get_bind()
        return cls(database_service.session, database_service=database_service,
                   session_factory=sessionmaker(bind=engine), **kwargs)
