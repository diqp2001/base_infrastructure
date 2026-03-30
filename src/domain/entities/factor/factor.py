"""
src/domain/entities/factor/factor.py
"""

from __future__ import annotations
from abc import ABC
from typing import ClassVar, Optional


class Factor(ABC):
    """Abstract base class for all factors."""
    

    FREQUENCIES: ClassVar[dict[str, dict]] = {
    "1s": {
        "label": "1 Second",
        "seconds": 1,
        "ibkr_label": "1 secs"
    },
    "5s": {
        "label": "5 Seconds",
        "seconds": 5,
        "ibkr_label": "5 secs"
    },
    "1m": {
        "label": "1 Minute",
        "seconds": 60,
        "ibkr_label": "1 min"
    },
    "5m": {
        "label": "5 Minutes",
        "seconds": 300,
        "ibkr_label": "5 mins"
    },
    "15m": {
        "label": "15 Minutes",
        "seconds": 900,
        "ibkr_label": "15 mins"
    },
    "1h": {
        "label": "1 Hour",
        "seconds": 3600,
        "ibkr_label": "1 hour"
    },
    "1d": {
        "label": "1 Day",
        "seconds": 86400,
        "ibkr_label": "1 day"
    },
    "1w": {
        "label": "1 Week",
        "seconds": 604800,
        "ibkr_label": "1 week"
    },
    "1mth": {
        "label": "1 Month (30d)",
        "seconds": 2592000,
        "ibkr_label": "1 month"
    },
    "1y": {
        "label": "1 Year (365d)",
        "seconds": 31536000,
        "ibkr_label": "1 month"
    },
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

    


