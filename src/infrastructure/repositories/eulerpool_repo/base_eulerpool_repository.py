"""
Base class of the Eulerpool repositories (the counterpart of BaseFMPRepository / BaseIBKRRepository).

Responsibilities: request Eulerpool through EulerpoolClient and normalize its answers. Persistence goes through the
local repositories (the factory); an Eulerpool repository never commits on its own.
"""

from __future__ import annotations

from typing import Optional


class BaseEulerpoolRepository:
    """An Eulerpool repository: the client, and the factory for the local repositories it stores through."""

    def __init__(self, eulerpool_client, factory=None):
        self.eulerpool_client = eulerpool_client
        self.factory = factory

    @staticmethod
    def symbol_of(entity) -> Optional[str]:
        """Eulerpool's identifier of a share entity: its ticker (Eulerpool also takes ISIN / CUSIP / SEDOL / WKN, but
        the share entities carry only the ticker)."""
        symbol = getattr(entity, "symbol", None) or getattr(entity, "ticker", None)
        return str(symbol).strip().upper() if symbol else None
