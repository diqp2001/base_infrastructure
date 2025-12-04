"""
Test Base Project Manager Package

A comprehensive trading system combining spatiotemporal momentum modeling,
factor creation, data storage, and backtesting capabilities.

This package integrates the best aspects of:
- Spatiotemporal Momentum Manager (core ML logic)
- Test Project Factor Creation (data infrastructure) 
- Test Project Backtest (backtesting engine)
"""

from .cross_sectionnal_project_manager import CrossSectionnal

__version__ = "1.0.0"
__all__ = ["CrossSectionnal"]