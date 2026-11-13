"""
FMP Factor Value Repository - company financial statements from Financial Modeling Prep as factor values (source
'fmp'): the shared StatementFactorValueRepository (fundamental_provider/) over the three FMP statement repositories.

Pipeline: FMP statement rows -> StatementRecord (fmp_repo/finance/financial_statements) -> raw CompanyShareFactor
series (group 'fundamental', subgroup = statement, frequency 1q | 1y, source 'fmp', name = the canonical field) ->
factor values stamped at the filing's publication, read as of the decision time. Storage, point in time and the
resolver hook (fetch_factor_value, FactorValueProviderPort) are the shared ones - see
statement_factor_value_repository.py.
"""

from __future__ import annotations

from typing import Optional

from src.infrastructure.repositories.fmp_repo.base_fmp_repository import BaseFMPRepository
from src.infrastructure.repositories.fmp_repo.finance.financial_statements.fmp_financial_statement_repository import (
    STATEMENT_REPOSITORIES,
)
from src.infrastructure.repositories.fmp_repo.fmp_client import FMPError
from src.infrastructure.repositories.fundamental_provider.statement_factor_value_repository import (
    StatementFactorValueRepository,
)

SOURCE = "fmp"


class FMPFactorValueRepository(BaseFMPRepository, StatementFactorValueRepository):
    """The FMP statements as raw fundamental factor values (the resolution service's 'fmp' family)."""

    def __init__(self, fmp_client, factory=None, limit: Optional[int] = None):
        BaseFMPRepository.__init__(self, fmp_client, factory)
        statements = {s: (cls(fmp_client, factory) if limit is None else cls(fmp_client, factory, limit=limit))
                      for s, cls in STATEMENT_REPOSITORIES.items()}
        StatementFactorValueRepository.__init__(self, SOURCE, "FMP", statements, factory=factory, errors=(FMPError,))
