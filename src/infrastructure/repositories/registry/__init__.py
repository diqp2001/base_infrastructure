"""
Repository Registry Package - Type-based dependency resolution for repositories.
"""

from .repository_registry import RepositoryRegistry, RepositoryProvider, auto_register_repositories

__all__ = [
    'RepositoryRegistry',
    'RepositoryProvider', 
    'auto_register_repositories'
]