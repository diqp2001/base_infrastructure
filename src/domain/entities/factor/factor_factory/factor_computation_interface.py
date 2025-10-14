from abc import ABC, abstractmethod
from typing import Any, Dict, Protocol

class FactorComputation(ABC):
    """
    Domain-level interface for factor computation.
    Defines the contract that all factor computation implementations must follow.
    """

    @abstractmethod
    def compute(
        self,
        input_data: Any,
        existing_factors: Dict[str, Any] | None = None,
        **params: Any
    ) -> Any:
        """
        Compute the factor from the given input data and parameters.

        Args:
            input_data: source data for the computation (e.g. price series)
            existing_factors: optional dict of existing computed factors
            params: additional factor-specific parameters

        Returns:
            Computed factor values (format defined by implementation).
        """
        pass
