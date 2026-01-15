"""
IBKR Repository Package - Interactive Brokers API-based repositories.

This package contains repositories that implement domain ports by interfacing
with the Interactive Brokers API for data acquisition and normalization.

Structure:
- finance/: Financial asset repositories (company shares, bonds, etc.)
- factor/: Factor and factor value repositories with IBKR tick data integration
- services/: Supporting services for contract mapping and data transformation
- tick_types/: IBKR tick type mappings and factor conversion utilities
"""

# Import main repository modules
from .factor import *
from .finance import *
from .services import *
from .tick_types import *

__all__ = []