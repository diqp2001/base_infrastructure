"""
IApi interface for API communication with external services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class IApi(ABC):
    """
    Interface for API communication with external services.
    Handles authentication, project management, and data upload/download.
    """
    
    @abstractmethod
    def authenticate(self, token: str) -> bool:
        """Authenticate with the API using the provided token."""
        pass
    
    @abstractmethod
    def create_project(self, name: str, language: str) -> Dict[str, Any]:
        """Create a new project."""
        pass
    
    @abstractmethod
    def read_project(self, project_id: int) -> Dict[str, Any]:
        """Read project details."""
        pass
    
    @abstractmethod
    def update_project(self, project_id: int, **kwargs) -> Dict[str, Any]:
        """Update project details."""
        pass
    
    @abstractmethod
    def delete_project(self, project_id: int) -> bool:
        """Delete a project."""
        pass