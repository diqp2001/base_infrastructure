"""
QuantConnect Lean Python Implementation - Complete Backtesting Framework

This module provides a comprehensive Python implementation of the QuantConnect Lean 
backtesting and live trading engine. It includes all major components needed for 
algorithmic trading including data management, backtesting engine, optimization, 
and API integration.

Modules:
- common: Core interfaces, data structures, and shared utilities
- data: Data acquisition, formatting, and consumption
- engine: Main backtesting and live trading engine
- algorithm_factory: Algorithm creation, loading, and compilation
- api: REST API client for QuantConnect platform integration
- launcher: System bootstrap and configuration management
- optimizer: Parameter optimization algorithms
- optimizer_launcher: Distributed optimization orchestration
- algorithm: Algorithm base classes and utilities
"""

# Re-export key components from all modules for easy access
from .common import *
from .data import *
from .engine import *
from .algorithm_factory import *
from .api import *
from .launcher import *
from .optimizer import *
from .optimizer_launcher import *

# Import algorithm module separately to avoid circular imports
try:
    from .algorithm import *
except ImportError:
    # Algorithm module might not be available in all contexts
    pass

__version__ = "1.0.0"
__author__ = "QuantConnect Lean Python Implementation"

__all__ = [
    # Core modules are exported via their own __all__ lists
    # This provides a clean namespace for users
]