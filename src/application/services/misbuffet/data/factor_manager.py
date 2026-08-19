"""
Generic FactorManager — base class for project-specific factor managers.
"""

import logging

from src.application.services.database_service.database_service import DatabaseService


class FactorManager:
    """
    Base factor manager.  Holds a database_service reference and a logger.
    Projects subclass this and add domain-specific factor creation / retrieval logic.
    """

    def __init__(self, database_service: DatabaseService):
        self.database_service = database_service
        self.logger = logging.getLogger(self.__class__.__name__)
