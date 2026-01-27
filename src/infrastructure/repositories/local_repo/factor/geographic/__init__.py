"""
Geographic factor repositories package.
"""

from .continent_factor_repository import ContinentFactorRepository
from .country_factor_repository import CountryFactorRepository

__all__ = [
    'ContinentFactorRepository',
    'CountryFactorRepository'
]