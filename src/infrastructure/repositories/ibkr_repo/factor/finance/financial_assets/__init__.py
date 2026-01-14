"""
IBKR Factor Financial Assets Module - Financial asset factor repositories for IBKR

This module contains IBKR implementations for financial asset factor repositories,
mirroring the structure of local_repo/factor/finance/financial_assets.
"""

from .ibkr_company_share_factor_repository import IBKRCompanyShareFactorRepository

__all__ = [
    'IBKRCompanyShareFactorRepository',
]