# src/infrastructure/mappers/__init__.py
"""
Mappers package for converting between domain entities and infrastructure models.

This package contains mapper classes that handle bidirectional conversion
between domain entities (pure business logic) and infrastructure models
(SQLAlchemy ORM models) following DDD principles.
"""

from .factor_dependency_mapper import FactorDependencyMapper

__all__ = [
    'FactorDependencyMapper'
]