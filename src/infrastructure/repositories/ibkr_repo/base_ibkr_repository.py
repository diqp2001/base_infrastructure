# src/infrastructure/repositories/base_ibkr_repository.py

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List

from ibapi.contract import Contract


# Domain Entity Type
EntityType = TypeVar("EntityType")
ModelType = TypeVar("ModelType")

class BaseIBKRRepository(ABC, Generic[EntityType,ModelType]):
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

    def _request_contract_details(self, contract: Contract) -> Optional[List[dict]]:
        """
        Request contract details from IBKR API.
        
        Args:
            contract: IBKR Contract object
            
        Returns:
            List of contract details dictionaries or None if not found
        """
        try:
            # Use the ib_client's get_contract_details method (standard pattern across repositories)
            contract_details = self.ib_client.get_contract_details(contract, timeout=15)
            
            if contract_details and len(contract_details) > 0:
                return contract_details
            else:
                return None
                
        except Exception as e:
            print(f"Error requesting IBKR contract details: {e}")
            return None

    def _validate_contract_details(self, details_list: Optional[List[dict]]) -> Optional[List[dict]]:
        """
        Validate contract details from IBKR API.
        
        Args:
            details_list: List of contract details dictionaries
            
        Returns:
            Validated contract details or None if invalid
        """
        if not details_list:
            return None
        
        # Basic validation - can be extended by subclasses
        return details_list

    def _to_entity(self, validated_details: List[dict]) -> EntityType:
        """
        Convert validated IBKR contract details to domain entity.
        
        Args:
            validated_details: Validated contract details from IBKR
            
        Returns:
            Domain entity
        """
        raise NotImplementedError("Subclasses must implement _to_entity or override get_or_create")

    def _build_contract(self, identifier: str) -> Contract:
        """
        Build an IBKR Contract object from a business identifier
        (symbol, conId, etc.).
        """
        raise NotImplementedError("Subclasses must implement _build_contract or override get_or_create")
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
