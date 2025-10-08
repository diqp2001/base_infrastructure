from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import uuid4


class FactorBase(ABC):
    """Abstract base class for all factors."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[str] = None,
    ):
        self.id = factor_id or str(uuid4())
        self.name = name
        self.group = group
        self.subgroup = subgroup
        self.data_type = data_type
        self.source = source
        self.definition = definition

    @abstractmethod
    def calculate(self, *args, **kwargs) -> Decimal:
        """Abstract method for calculating the factor value."""
        pass

    def describe(self) -> str:
        return (
            f"Factor[{self.id}] - {self.name}\n"
            f"Group: {self.group}, Subgroup: {self.subgroup}\n"
            f"Type: {self.data_type}, Source: {self.source}\n"
            f"Definition: {self.definition}"
        )


