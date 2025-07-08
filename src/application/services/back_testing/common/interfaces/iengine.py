"""
IEngine interface for the main execution engine.
"""

from abc import ABC, abstractmethod


class IEngine(ABC):
    """
    Interface for the main execution engine.
    Orchestrates algorithm execution, data feeds, and result processing.
    """
    
    @abstractmethod
    def initialize_algorithm(self, algorithm: 'IAlgorithm') -> None:
        """Initialize the algorithm for execution."""
        pass
    
    @abstractmethod
    def run(self) -> None:
        """Run the algorithm."""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop the algorithm execution."""
        pass
    
    @abstractmethod
    def dispose(self) -> None:
        """Clean up engine resources."""
        pass