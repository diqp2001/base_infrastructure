"""
Read-only access for the research / backtest registry web pages and API (2026-11-18).

The web process only READS: its engine carries the monitor's write guard (``guard_read_only``: every statement that
is not a SELECT / WITH is refused before it reaches SQL Server) and, when configured, the read-only SQL login of the
Docker monitor (DB_READONLY_USER, db_datareader). It never builds DatabaseService (which creates missing tables).
Long backtests never run in the web process: they run in their own worker (python -m <project manager>, the
/strategies launcher's ExperimentService.JobRunner, or a Docker job).

    factory = query_service_factory()            # () -> ResearchQueryService on a fresh read-only session
"""

from __future__ import annotations

from typing import Callable, Optional

from src.application.services.backtest_registry.research_query_service import ResearchQueryService


def read_only_engine(url=None):
    from src.infrastructure.database.settings import get_database_url, get_readonly_database_url
    from src.infrastructure.repositories.local_repo.monitoring.monitoring_read_repository import (
        create_read_only_engine,
    )
    return create_read_only_engine(url or get_readonly_database_url() or get_database_url("sql_server"))


def query_service_factory(engine=None) -> Callable[[], ResearchQueryService]:
    from sqlalchemy.orm import sessionmaker
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    session_factory = sessionmaker(bind=engine or read_only_engine())

    def make(session=None) -> ResearchQueryService:
        return ResearchQueryService(RepositoryFactory(session or session_factory()))
    return make


def close(service: Optional[ResearchQueryService]) -> None:
    if service is not None:
        try:
            service.factory.session.close()
        except Exception:
            pass
