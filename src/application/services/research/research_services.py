"""
ResearchServices — wires the factor research use cases onto a database session (what the Flask routes use).

The repository factory is built WITHOUT an IBKR client: research and factor analysis only read what is stored.
Factor value generation runs in its own worker process (factor_generation) with the engine's import path.
"""

from __future__ import annotations

from typing import List, Optional

from src.application.services.research.factor_returns import FactorReturnService, database_market_closes
from src.application.services.research.project_returns import ProjectReturnsService, ResultSource


class ResearchServices:

    def __init__(self, session, factor_return_store=None, returns_service: Optional[ProjectReturnsService] = None):
        from src.infrastructure.repositories.repository_factory import RepositoryFactory
        from src.infrastructure.research.factor_return_files import FactorReturnFileStore, FrenchLibraryImporter
        self.session = session
        self.factory = RepositoryFactory(session)                     # local repositories only, no IBKR
        self.store = factor_return_store or FactorReturnFileStore()
        self.importer = FrenchLibraryImporter(self.store)
        self.factor_returns = FactorReturnService(self.store, market_closes=lambda: database_market_closes(self.factory))
        self.returns = returns_service or ProjectReturnsService(experiment_sources=self._experiment_sources)
        from src.application.services.research.factor_generation import FactorGenerationService, GenerationJobs
        from src.application.services.research.factor_research import FactorResearchData, FactorResearchService
        self.data = FactorResearchData(self.factory)
        self.research = FactorResearchService(self.data)
        self.generation = FactorGenerationService(self.factory, data=self.data)
        self.jobs = GenerationJobs()

    def save_mimicking_portfolio(self, name: str, long_short, frequency: str, description: str):
        """Store a factor's long-short quantile return series (decision-stamped) as a custom factor return,
        re-stamped at the bar where each return is realised, so the factor analysis aligns it correctly."""
        import pandas as pd
        from src.application.services.research.factor_research import bar_minutes_of
        from src.application.services.research.project_returns import realised_index
        from src.domain.entities.research.factor_models import MIMICKING_PORTFOLIO
        s = pd.Series(long_short, dtype=float).dropna()
        if len(s) < 3:
            raise ValueError("the long-short series has fewer than 3 returns")
        realised = realised_index(s.index, bar_minutes_of(frequency))
        frame = pd.DataFrame({name.upper(): s.to_numpy()}, index=realised)
        return self.store.save(name, frame, kind=MIMICKING_PORTFOLIO, frequency=frequency, source=description,
                               notes="Long-short (top minus bottom quantile) equal-weight portfolio of a stored "
                                     "characteristic; returns re-stamped at the bar where they are realised.")

    def _experiment_sources(self) -> List[ResultSource]:
        """Succeeded strategy experiments (their own results folders) as results sources."""
        repo = self.factory.get_local_repository("StrategyExperiment")
        if repo is None:
            return []
        out = []
        for e in repo.get_by_status("succeeded"):
            kind = "csm" if e.project_key.startswith("cross_sectional") else "stm"
            out.append(ResultSource(f"experiment:{e.id}", f"Strategy experiment #{e.id} ({e.project_key})", kind,
                                    (lambda d=e.results_dir: d)))
        return out
