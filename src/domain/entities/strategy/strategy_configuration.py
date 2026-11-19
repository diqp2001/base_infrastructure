"""
Backward-compatible names: StrategyConfiguration was replaced by Strategy (2026-11-19, ``strategy.py``).

Kept only so old imports keep working; new code imports from ``src.domain.entities.strategy.strategy``.
"""

from src.domain.entities.strategy.strategy import (  # noqa: F401
    ARCHIVED,
    DRAFT,
    LOCKED,
    STATUSES,
    VALIDATED,
    Strategy,
    StrategyLocked,
    canonical_json,
    content_hash,
)

StrategyConfiguration = Strategy
ConfigurationLocked = StrategyLocked
