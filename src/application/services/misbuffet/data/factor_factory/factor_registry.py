from typing import Dict, Type
from .base_factor_creator import BaseFactorCreator
from .implementations.moving_average import MovingAverageFactor
from .implementations.momentum import MomentumFactor

class FactorRegistry:
    _registry: Dict[str, Type[BaseFactorCreator]] = {}

    @classmethod
    def register(cls, name: str, creator_cls: Type[BaseFactorCreator]):
        cls._registry[name] = creator_cls

    @classmethod
    def get(cls, name: str) -> Type[BaseFactorCreator]:
        if name not in cls._registry:
            raise ValueError(f"Unknown factor: {name}")
        return cls._registry[name]

    @classmethod
    def list_factors(cls):
        return list(cls._registry.keys())


# register defaults
FactorRegistry.register("moving_average", MovingAverageFactor)
FactorRegistry.register("momentum", MomentumFactor)
