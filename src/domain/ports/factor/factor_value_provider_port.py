from abc import ABC, abstractmethod
from typing import Optional
from src.domain.entities.factor.factor_value import FactorValue


class FactorValueProviderPort(ABC):
    """A data provider's factor value repository (IBKR, FMP, ...): the value of a raw (stored, not calculated) series
    for an entity at a time - from the store when it is there, else fetched from the provider, stored through the local
    FactorValueRepository and returned. None when the provider has no value usable at that time (never a look-ahead,
    never a default).

    FactorValueResolutionService reaches every provider through this port (RepositoryFactory.factor_value_provider(
    family)); which series a provider serves (its source, its groups) is the provider's own rule."""

    @abstractmethod
    def fetch_factor_value(self, factor_entity, entity, time_date, **kwargs) -> Optional[FactorValue]: ...
