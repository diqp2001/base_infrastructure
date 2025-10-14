from typing import Any, Dict
from .factor_registry import FactorRegistry

class FactorFactory:
    """
    Application-level service for creating and computing factors.
    """

    def __init__(self):
        pass

    def create(
        self,
        factor_name: str,
        input_data: Any,
        existing_factors: Dict[str, Any] | None = None,
        **params
    ):
        creator_cls = FactorRegistry.get(factor_name)
        creator = creator_cls()
        return creator.compute(input_data=input_data, existing_factors=existing_factors, **params)
