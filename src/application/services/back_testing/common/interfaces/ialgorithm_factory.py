"""
IAlgorithmFactory interface for algorithm factories.
"""

from abc import ABC, abstractmethod


class IAlgorithmFactory(ABC):
    """
    Interface for algorithm factories.
    Creates and loads algorithm instances.
    """
    
    @abstractmethod
    def create_algorithm_instance(self, algorithm_name: str, **kwargs) -> 'IAlgorithm':
        """Create an instance of the specified algorithm."""
        pass
    
    @abstractmethod
    def load_algorithm(self, path: str) -> 'IAlgorithm':
        """Load an algorithm from the specified path."""
        pass