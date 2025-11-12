"""
src/domain/entities/factor/factor.py
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


class Factor(ABC):
    """Abstract base class for all factors."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
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

    

    def describe(self) -> str:
        return (
            f"Factor[{self.id}] - {self.name}\n"
            f"Group: {self.group}, Subgroup: {self.subgroup}\n"
            f"Type: {self.data_type}, Source: {self.source}\n"
            f"Definition: {self.definition}"
        )


