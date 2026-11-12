"""
Base class of the Financial Modeling Prep repositories (the counterpart of BaseIBKRRepository).

Responsibilities: request FMP through FMPClient and normalize its rows. Persistence goes through the local
repositories (the factory); an FMP repository never commits on its own.
"""

from __future__ import annotations

from typing import Optional


class BaseFMPRepository:
    """An FMP repository: the client, and the factory for the local repositories it stores through."""

    def __init__(self, fmp_client, factory=None):
        self.fmp_client = fmp_client
        self.factory = factory

    @staticmethod
    def symbol_of(entity) -> Optional[str]:
        """The provider's symbol of a share entity."""
        symbol = getattr(entity, "symbol", None) or getattr(entity, "ticker", None)
        return str(symbol).strip().upper() if symbol else None
