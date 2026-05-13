"""
Holding Service - handles holding value calculations and factor-related operations.

This service handles factor value calculations for holdings while pure entity operations
go through repositories, following DDD principles.
"""

import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)


class HoldingService:
    """
    Service for holding value calculations and factor-related operations.
    
    Responsibilities:
    - Calculate holding values using position services and market data
    - Handle factor calculations related to holdings
    - Coordinate between repository entity operations and service value calculations
    """
    
    def __init__(self, session, factory):
        """
        Initialize holding service with database session and factory.
        
        Args:
            session: Database session for repository access
            factory: Factory for creating repository instances
        """
        self.session = session
        self.factory = factory
        self.logger = logger
    
    def calculate_value(self, holding_id: int, as_of_date: Optional[datetime] = None) -> Decimal:
        """
        Calculate the value of a specific holding.
        
        This method uses PositionService for factor value calculations and the holding 
        repository's get_related_position function for entity operations.
        
        Args:
            holding_id: ID of the holding to value
            as_of_date: Date for which to calculate value (defaults to current date)
            
        Returns:
            Decimal: Total holding value
            
        Raises:
            ValueError: If holding not found or calculation fails
        """
        try:
            if as_of_date is None:
                as_of_date = datetime.now()
            
            # Get holding entity through repository (pure entity operation)
            from src.infrastructure.repositories.local_repo.finance.holding.holding_repository import HoldingRepository
            holding_repo = HoldingRepository(self.session, self.factory)
            
            holding = holding_repo.get_by_id(holding_id)
            if not holding:
                raise ValueError(f"Holding {holding_id} not found")
            
            # Get related position through repository (pure entity operation)
            position = holding_repo.get_related_position(holding_id)
            
            if not position:
                self.logger.info(f"No position found for holding {holding_id}, returning 0 value")
                return Decimal('0.00')
            
            # Calculate value using PositionService for factor calculations
            from src.application.services.data.entities.factor.finance.position_service import PositionService
            position_service = PositionService(self.session, self.factory)
            
            position_value = position_service.calculate_value(position.id, as_of_date)
            
            self.logger.info(f"Holding {holding_id} value calculated: {position_value}")
            return position_value
            
        except Exception as e:
            self.logger.error(f"Error calculating holding {holding_id} value: {str(e)}")
            raise
    
    def get_holding_details(self, holding_id: int, as_of_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get detailed information about a holding including its value breakdown.
        
        Args:
            holding_id: ID of the holding
            as_of_date: Date for which to get details
            
        Returns:
            Dict containing holding details and value breakdown
        """
        try:
            if as_of_date is None:
                as_of_date = datetime.now()
            
            # Get holding through repository
            from src.infrastructure.repositories.local_repo.finance.holding.holding_repository import HoldingRepository
            holding_repo = HoldingRepository(self.session, self.factory)
            
            holding = holding_repo.get_by_id(holding_id)
            if not holding:
                raise ValueError(f"Holding {holding_id} not found")
            
            # Get related position
            position = holding_repo.get_related_position(holding_id)
            
            # Calculate value using services
            holding_value = self.calculate_value(holding_id, as_of_date)
            
            # Build details response
            details = {
                'holding_id': holding_id,
                'asset_id': holding.asset_id,
                'container_id': holding.container_id,
                'start_date': holding.start_date,
                'end_date': holding.end_date,
                'is_active': holding.is_active() if hasattr(holding, 'is_active') else True,
                'value': holding_value,
                'as_of_date': as_of_date,
                'position': None
            }
            
            if position:
                details['position'] = {
                    'position_id': position.id,
                    'quantity': position.quantity,
                    'position_type': position.position_type.value if hasattr(position.position_type, 'value') else str(position.position_type)
                }
            
            return details
            
        except Exception as e:
            self.logger.error(f"Error getting holding {holding_id} details: {str(e)}")
            raise
    
    def calculate_quantity_value(self, holding_id: int, price_per_unit: Decimal, as_of_date: Optional[datetime] = None) -> Decimal:
        """
        Calculate holding value based on a specific price per unit.
        
        This is useful for mark-to-market calculations when you have external pricing data.
        
        Args:
            holding_id: ID of the holding
            price_per_unit: Price per unit of the holding
            as_of_date: Date for the calculation
            
        Returns:
            Decimal: Calculated value (quantity * price_per_unit)
        """
        try:
            # Get holding and its position
            from src.infrastructure.repositories.local_repo.finance.holding.holding_repository import HoldingRepository
            holding_repo = HoldingRepository(self.session, self.factory)
            
            position = holding_repo.get_related_position(holding_id)
            if not position:
                self.logger.warning(f"No position found for holding {holding_id}")
                return Decimal('0.00')
            
            # Calculate value
            quantity = Decimal(str(position.quantity))
            total_value = quantity * price_per_unit
            
            self.logger.info(f"Holding {holding_id}: quantity {quantity} * price {price_per_unit} = {total_value}")
            return total_value
            
        except Exception as e:
            self.logger.error(f"Error calculating quantity value for holding {holding_id}: {str(e)}")
            raise