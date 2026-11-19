"""
src/domain/ports/universe/universe_port.py

Abstract ports of the universe repositories: Universe (any type, with its members), its two kinds of member, and
the InvestmentUniverse kept by the projects.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from src.domain.entities.universe.universe import Universe
from src.domain.entities.universe.universe_factor import UniverseFactor
from src.domain.entities.universe.universe_financial_asset import UniverseFinancialAsset


class UniversePort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[Universe]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Universe]: ...

    @abstractmethod
    def get_all(self) -> List[Universe]: ...

    @abstractmethod
    def add(self, entity: Universe) -> Optional[Universe]: ...

    @abstractmethod
    def update(self, entity: Universe) -> Optional[Universe]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[Universe]: ...


class UniverseFinancialAssetPort(ABC):

    @abstractmethod
    def get_by_universe(self, universe_id: int, on: Optional[date] = None) -> List[UniverseFinancialAsset]: ...

    @abstractmethod
    def add(self, entity: UniverseFinancialAsset) -> UniverseFinancialAsset: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...


class UniverseFactorPort(ABC):

    @abstractmethod
    def get_by_universe(self, universe_id: int) -> List[UniverseFactor]: ...

    @abstractmethod
    def add(self, entity: UniverseFactor) -> UniverseFactor: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...
