"""
src/domain/entities/factor/factor.py
"""

from __future__ import annotations
from abc import ABC
from typing import ClassVar, Optional


class Factor(ABC):
    """Abstract base class for all factors."""
    # Centralized frequency registry (domain-level concept)
    FREQUENCIES: ClassVar[dict[str, dict]] = {
        "1s": {"label": "1 Second", "seconds": 1},
        "5s": {"label": "5 Seconds", "seconds": 5},
        "1m": {"label": "1 Minute", "seconds": 60},
        "5m": {"label": "5 Minutes", "seconds": 300},
        "15m": {"label": "15 Minutes", "seconds": 900},
        "1h": {"label": "1 Hour", "seconds": 3600},
        "1d": {"label": "1 Day", "seconds": 86400},
        "1w": {"label": "1 Week", "seconds": 604800},
        "1mth": {"label": "1 Month (30d)", "seconds": 2592000},
        "1y": {"label": "1 Year (365d)", "seconds": 31536000},
    }
    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
    ):
        self.id = factor_id  # Repository will assign sequential ID if None
        self.name = name
        self.group = group
        self.subgroup = subgroup
        
        self.data_type = data_type
        self.source = source
        self.definition = definition

        if frequency is not None and frequency not in self.FREQUENCIES:
                raise ValueError(f"Invalid frequency '{frequency}'. "f"Allowed values: {list(self.FREQUENCIES.keys())}")
        self.frequency = frequency

    


