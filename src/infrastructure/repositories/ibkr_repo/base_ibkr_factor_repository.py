"""
Base IBKR Factor Repository - Foundation for all IBKR factor-related repositories

This repository provides common functionality for IBKR factor operations
while maintaining the ports & adapters architecture.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from abc import ABC, abstractmethod

from src.infrastructure.repositories.ibkr_repo.base_ibkr_repository import BaseIBKRRepository
from src.domain.entities.factor.factor_value import FactorValue


class BaseIBKRFactorRepository(BaseIBKRRepository):
    """
    Base class for all IBKR factor repositories.
    
    Provides common functionality for:
    - IBKR tick data processing
    - Factor value creation from IBKR data
    - Delegation to local repositories for persistence
    """

    def __init__(self, ibkr_client, local_repo):
        """
        Initialize base IBKR factor repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            local_repo: Local repository for persistence operations
        """
        super().__init__(ibkr_client)
        self.local_repo = local_repo

    def _create_factor_value_from_ibkr_data(
        self,
        factor_id: int,
        entity_id: int,
        ibkr_data: Dict[str, Any],
        date_obj: date
    ) -> Optional[FactorValue]:
        """
        Create factor value from IBKR data.
        
        Args:
            factor_id: The factor ID
            entity_id: The entity ID (instrument or financial asset)
            ibkr_data: Raw IBKR data dictionary
            date_obj: Date for the factor value
            
        Returns:
            FactorValue entity or None if creation failed
        """
        try:
            # Extract value from IBKR data based on factor type
            value = self._extract_value_for_factor(factor_id, ibkr_data)
            if value is None:
                return None

            return FactorValue(
                id=None,  # Will be set by repository
                factor_id=factor_id,
                entity_id=entity_id,
                date=date_obj,
                value=str(value)
            )
            
        except Exception as e:
            print(f"Error creating factor value from IBKR data: {e}")
            return None

    
    def _extract_value_for_factor(self, factor_id: int, ibkr_data: Dict[str, Any]) -> Optional[Any]:
        """
        Extract specific factor value from IBKR data.
        
        This method must be implemented by concrete repositories based on
        their specific factor extraction logic.
        
        Args:
            factor_id: The factor ID to extract
            ibkr_data: Raw IBKR data dictionary
            
        Returns:
            Extracted value or None if not available
        """
        pass

    def _validate_factor_value_data(self, factor_id: int, entity_id: int, time: str) -> bool:
        """
        Validate factor value creation parameters.
        
        Args:
            factor_id: The factor ID
            entity_id: The entity ID
            time: Date string in 'YYYY-MM-DD' format
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not isinstance(factor_id, int) or factor_id <= 0:
                print(f"Invalid factor_id: {factor_id}")
                return False
                
            if not isinstance(entity_id, int) or entity_id <= 0:
                print(f"Invalid entity_id: {entity_id}")
                return False
                
            # Validate date format
            datetime.strptime(time, '%Y-%m-%d')
            return True
            
        except ValueError:
            print(f"Invalid date format: {time}")
            return False
        except Exception as e:
            print(f"Validation error: {e}")
            return False

    def _check_existing_factor_value(self, factor_id: int, entity_id: int, time: str) -> Optional[FactorValue]:
        """
        Check if factor value already exists for the given parameters.
        
        Args:
            factor_id: The factor ID
            entity_id: The entity ID
            time: Date string in 'YYYY-MM-DD' format
            
        Returns:
            Existing FactorValue or None if not found
        """
        try:
            # Check if we have the method available
            if hasattr(self.local_repo, 'get_by_factor_entity_date'):
                return self.local_repo.get_by_factor_entity_date(factor_id, entity_id, time)
            elif hasattr(self.local_repo, 'local_factor_value_repo'):
                return self.local_repo.local_factor_value_repo.get_by_factor_entity_date(
                    factor_id, entity_id, time
                )
            else:
                print("Local repository doesn't have factor value lookup capability")
                return None
                
        except Exception as e:
            print(f"Error checking existing factor value: {e}")
            return None