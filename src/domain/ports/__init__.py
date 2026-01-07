"""
Domain Ports - Interfaces for repository and service contracts.

This module contains abstract base classes (ports) that define contracts
for infrastructure adapters following the Ports & Adapters pattern.
"""

# Core entity ports
from .continent_port import ContinentPort
from .country_port import CountryPort
from .industry_port import IndustryPort
from .sector_port import SectorPort

# Factor ports
from .factor.factor_port import FactorPort
from .factor.continent_factor_port import ContinentFactorPort
from .factor.country_factor_port import CountryFactorPort

# Finance ports
from .finance.company_port import CompanyPort

# Time series ports
from .time_series.time_series_port import TimeSeriesPort

__all__ = [
    # Core entity ports
    'ContinentPort',
    'CountryPort', 
    'IndustryPort',
    'SectorPort',
    
    # Factor ports
    'FactorPort',
    'ContinentFactorPort',
    'CountryFactorPort',
    
    # Finance ports
    'CompanyPort',
    
    # Time series ports
    'TimeSeriesPort',
]