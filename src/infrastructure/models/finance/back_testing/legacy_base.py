"""
A declarative base of its own for the legacy back-testing models (bars, ticks, symbols, back-testing enums).

They were never created in the application database and are used only by legacy mappers. Giving them their own
metadata keeps them out of ``ModelBase.metadata`` — the application's one registry, the schema Alembic manages — even
when a legacy module is imported (before 2026-11-23 an import added their 19 tables to the application schema).
"""

from sqlalchemy.orm import DeclarativeBase


class LegacyBackTestingBase(DeclarativeBase):
    """Base of the legacy back-testing tables (not managed by the application's migrations)."""
