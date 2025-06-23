# src/application/managers/manager.py
from abc import ABC, abstractmethod
import logging
"""Explanation: The Manager class serves as 
an abstract base class for all managers, providing 
a logger and an optional setup method for additional
 initialization. Each subclass of Manager should implement 
the execute method to define its specific tasks."""
class Manager(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.setup()

    def setup(self):
        """Optional setup method for additional initialization."""
        pass

    @abstractmethod
    def execute(self):
        """Define primary actions to be overridden in each manager."""
        pass
