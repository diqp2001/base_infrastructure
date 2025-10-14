from src.domain.entities.factor.factor_factory.factor_computation_interface import FactorComputation

class BaseFactorCreator(FactorComputation):
    """
    Base implementation of the FactorComputation interface.
    Provides a consistent structure and optional validation helpers.
    """
    def validate_inputs(self, *args, **kwargs):
        pass  # Add optional validation logic shared by all factors
