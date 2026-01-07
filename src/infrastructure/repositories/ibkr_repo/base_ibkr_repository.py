# src/infrastructure/repositories/base_ibkr_repository.py

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List

from ibapi.contract import Contract


# Domain Entity Type
EntityType = TypeVar("EntityType")

class BaseIBKRRepository(ABC, Generic[EntityType]):
    """
    Base class for all IBKR repositories.

    Responsibilities:
    - Interact with IBKR (via ibapi)
    - Build IBKR Contract / request objects
    - Normalize IBKR responses
    - Convert IBKR objects → Domain entities

    This class DOES NOT:
    - Persist data
    - Know about ORM models
    - Commit anything to a database
    """

    def __init__(self, ib_client):
        """
        Args:
            ib_client: Connected IBKR client (wrapper around ibapi)
        """
        self.ib_client = ib_client

    # ------------------------------------------------------------------
    # IBKR REQUEST LAYER
    # ------------------------------------------------------------------

    @abstractmethod
    def _build_contract(self, identifier: str) -> Contract:
        """
        Build an IBKR Contract object from a business identifier
        (symbol, conId, etc.).
        """
        pass

    

  
    # ------------------------------------------------------------------
    # PUBLIC DOMAIN-FACING API
    # ------------------------------------------------------------------

    def get_or_create(self, identifier: str) -> EntityType:
        """
        Fetch data from IBKR and return a Domain entity.

        NOTE:
        - "create" here means creating a Domain object,
          NOT persisting it.
        """
        contract = self._build_contract(identifier)
        details_list = self._request_contract_details(contract)
        validated_details = self._validate_contract_details(details_list)
        return self._to_entity(validated_details)
