"""
Portfolio Service - handles portfolio value calculations and factor-related operations.

This service orchestrates portfolio valuation using holding services and repository operations,
following the DDD principle where pure entity operations go through repositories and 
factor value-related operations go through services.
"""

import logging
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)


class PortfolioService:
    """
    Service for portfolio value calculations and factor-related operations.
    
    Responsibilities:
    - Calculate portfolio values using holding services
    - Orchestrate factor calculations across portfolio entities
    - Coordinate between repository entity operations and service value calculations
    """
    
    def __init__(self, session, factory):
        """
        Initialize portfolio service with database session and factory.
        
        Args:
            session: Database session for repository access
            factory: Factory for creating repository instances
        """
        self.session = session
        self.factory = factory
        self.logger = logger
    
    def calculate_value(self, portfolio_id: int, as_of_date: Optional[datetime] = None) -> Decimal:
        """
        Calculate the total value of a portfolio by summing its holding values.
        
        This method uses HoldingService for factor value calculations and the portfolio 
        repository's get_related_holdings function for entity operations.
        
        Args:
            portfolio_id: ID of the portfolio to value
            as_of_date: Date for which to calculate value (defaults to current date)
            
        Returns:
            Decimal: Total portfolio value
            
        Raises:
            ValueError: If portfolio not found or calculation fails
        """
        try:
            if as_of_date is None:
                as_of_date = datetime.now()
            
            # Get portfolio entity through repository (pure entity operation)
            from src.infrastructure.repositories.local_repo.finance.portfolio.portfolio_repository import PortfolioRepository
            portfolio_repo = PortfolioRepository(self.session, self.factory)
            
            portfolio = portfolio_repo.get_by_id(portfolio_id)
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")
            
            # Get related holdings through repository (pure entity operation)
            holdings = portfolio_repo.get_related_holdings(portfolio_id)
            
            if not holdings:
                self.logger.info(f"No holdings found for portfolio {portfolio_id}, returning 0 value")
                return Decimal('0.00')
            
            # Calculate total value using HoldingService for factor calculations
            from src.application.services.data.entities.factor.finance.holding_service import HoldingService
            holding_service = HoldingService(self.session, self.factory)
            
            total_value = Decimal('0.00')
            
            for holding in holdings:
                try:
                    holding_value = holding_service.calculate_value(holding.id, as_of_date)
                    total_value += holding_value
                    self.logger.debug(f"Added holding {holding.id} value {holding_value} to portfolio total")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to calculate value for holding {holding.id}: {str(e)}")
                    # Continue with other holdings
            
            self.logger.info(f"Portfolio {portfolio_id} total value calculated: {total_value}")
            return total_value
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio {portfolio_id} value: {str(e)}")
            raise
    
    def get_portfolio_breakdown(self, portfolio_id: int, as_of_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get detailed breakdown of portfolio value by holdings.
        
        Args:
            portfolio_id: ID of the portfolio
            as_of_date: Date for which to calculate breakdown
            
        Returns:
            Dict containing portfolio details and holding breakdown
        """
        try:
            if as_of_date is None:
                as_of_date = datetime.now()
            
            # Get portfolio and holdings through repository
            from src.infrastructure.repositories.local_repo.finance.portfolio.portfolio_repository import PortfolioRepository
            portfolio_repo = PortfolioRepository(self.session, self.factory)
            
            portfolio = portfolio_repo.get_by_id(portfolio_id)
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")
            
            holdings = portfolio_repo.get_related_holdings(portfolio_id)
            
            # Calculate breakdown using services
            from src.application.services.data.entities.factor.finance.holding_service import HoldingService
            holding_service = HoldingService(self.session, self.factory)
            
            holding_details = []
            total_value = Decimal('0.00')
            
            for holding in holdings:
                try:
                    holding_value = holding_service.calculate_value(holding.id, as_of_date)
                    holding_details.append({
                        'holding_id': holding.id,
                        'asset_id': holding.asset_id,
                        'value': holding_value,
                        'container_id': holding.container_id
                    })
                    total_value += holding_value
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get breakdown for holding {holding.id}: {str(e)}")
            
            return {
                'portfolio_id': portfolio_id,
                'portfolio_name': portfolio.name,
                'total_value': total_value,
                'as_of_date': as_of_date,
                'holdings_count': len(holdings),
                'holdings_breakdown': holding_details
            }
            
        except Exception as e:
            self.logger.error(f"Error getting portfolio {portfolio_id} breakdown: {str(e)}")
            raise