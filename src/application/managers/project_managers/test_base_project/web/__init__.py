"""
Web interface module for test_base_project.

This module provides web-based monitoring and control capabilities for the
hybrid trading system, integrating with the existing Misbuffet web framework.
"""

from .web_interface_manager import WebInterfaceManager
from .progress_monitor import ProgressMonitor

__all__ = [
    'WebInterfaceManager',
    'ProgressMonitor'
]