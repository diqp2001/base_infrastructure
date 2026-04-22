"""
Portfolio Repository - handles CRUD operations for Portfolio entities.

Follows the standardized repository pattern with _create_or_get_* methods
consistent with other repositories in the codebase.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from decimal import Decimal

logger = logging.getLogger(__name__)

from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel as PortfolioModel
from src.domain.entities.finance.portfolio.portfolio import (
    Portfolio as PortfolioEntity
)
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.finance.portfolio_mapper import PortfolioMapper
from src.domain.ports.finance.portfolio.portfolio_port import PortfolioPort


class PortfolioRepository(BaseLocalRepository, PortfolioPort):
    """Repository for managing Portfolio entities."""
    
    def __init__(self, session: Session, factory, mapper: PortfolioMapper = None):
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or PortfolioMapper()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Portfolio."""
        return PortfolioModel
    
    def _to_entity(self, model: PortfolioModel) -> PortfolioEntity:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        return self.mapper.to_domain(model)
    
    def _to_model(self, entity: PortfolioEntity) -> PortfolioModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        return self.mapper.to_orm(entity)
        
    
    def get_all(self) -> List[PortfolioEntity]:
        """Retrieve all Portfolio records."""
        models = self.session.query(PortfolioModel).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_id(self, portfolio_id: int) -> Optional[PortfolioEntity]:
        """Retrieve a Portfolio by its ID."""
        model = self.session.query(PortfolioModel).filter(
            PortfolioModel.id == portfolio_id
        ).first()
        return self._to_entity(model)
    
    def get_by_name(self, name: str) -> Optional[PortfolioEntity]:
        """Retrieve a portfolio by name."""
        model = self.session.query(PortfolioModel).filter(
            PortfolioModel.name == name
        ).first()
        return self._to_entity(model)
    
    def get_by_backtest_id(self, backtest_id: str) -> List[PortfolioEntity]:
        """Retrieve portfolios by backtest ID."""
        models = self.session.query(PortfolioModel).filter(
            PortfolioModel.backtest_id == backtest_id
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_owner_id(self, owner_id: int) -> List[PortfolioEntity]:
        """Retrieve portfolios by owner ID."""
        models = self.session.query(PortfolioModel).filter(
            PortfolioModel.owner_id == owner_id
        ).all()
        return [self._to_entity(model) for model in models]
    
    def exists_by_name(self, name: str) -> bool:
        """Check if a Portfolio exists by name."""
        return self.session.query(PortfolioModel).filter(
            PortfolioModel.name == name
        ).first() is not None
    
    def add(self, entity: PortfolioEntity) -> PortfolioEntity:
        """Add a new Portfolio entity to the database."""
        # Check for existing portfolio with same name
        if self.exists_by_name(entity.name):
            existing = self.get_by_name(entity.name)
            return existing
        
        model = self._to_model(entity)
        self.session.add(model)
        self.session.commit()
        
        return self._to_entity(model)
    
    def update(self, portfolio_id: int, **kwargs) -> Optional[PortfolioEntity]:
        """Update an existing Portfolio record."""
        model = self.session.query(PortfolioModel).filter(
            PortfolioModel.id == portfolio_id
        ).first()
        
        if not model:
            return None
        
        for attr, value in kwargs.items():
            if hasattr(model, attr):
                setattr(model, attr, value)
        
        self.session.commit()
        return self._to_entity(model)
    
    def delete(self, portfolio_id: int) -> bool:
        """Delete a Portfolio record by ID."""
        model = self.session.query(PortfolioModel).filter(
            PortfolioModel.id == portfolio_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        self.session.commit()
        return True
    
    def _get_next_available_portfolio_id(self) -> int:
        """
        Get the next available ID for portfolio creation.
        Returns the next sequential ID based on existing database records.
        
        Returns:
            int: Next available ID (defaults to 1 if no records exist)
        """
        try:
            max_id_result = self.session.query(PortfolioModel.id).order_by(PortfolioModel.id.desc()).first()
            
            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist
                
        except Exception as e:
            print(f"Warning: Could not determine next available portfolio ID: {str(e)}")
            return 1  # Default to 1 if query fails
    
    def get_or_create(self, name: str, portfolio_type: str = "STANDARD",
                     initial_cash: float = 100000.0, currency_code: str = "USD",
                     owner_id: Optional[int] = None) -> Optional[PortfolioEntity]:
        """
        Get or create a portfolio with dependency resolution.
        
        Args:
            name: Portfolio name (required)
            portfolio_type: Type of portfolio (STANDARD, RETIREMENT, BACKTEST, etc.)
            initial_cash: Initial cash amount (default: 100000.0)
            currency_code: Currency ISO code (default: USD)
            owner_id: Owner ID (optional)
            
        Returns:
            Portfolio entity or None if creation failed
        """
        return self._create_or_get(name, portfolio_type=portfolio_type, 
                                  initial_cash=initial_cash, currency=currency_code, 
                                  owner_id=owner_id)

    def _create_or_get(self, name: str, **kwargs) -> Optional[PortfolioEntity]:
        """
        Create portfolio entity if it doesn't exist, otherwise return existing.
        Follows the standard _create_or_get pattern from Repository_Local_CreateOrGet_CLAUDE.md
        
        Args:
            name: Portfolio name (unique identifier)
            **kwargs: Additional portfolio parameters
                - portfolio_type: Type of portfolio (default: "STANDARD")
                - initial_cash: Initial cash amount (default: 100000.0)
                - currency: Portfolio currency (default: "USD")
                - owner_id: Owner ID (optional)
                - inception_date: Portfolio inception date (default: today)
                - created_at: Creation timestamp (default: now)
            
        Returns:
            PortfolioEntity: Created or existing portfolio entity
            
        Raises:
            DatabaseError: If database operation fails
            ValidationError: If required parameters are invalid
        """
        try:
            # Step 1: Check if entity already exists by unique identifier
            existing_portfolio = self.get_by_name(name)
            if existing_portfolio:
                logger.debug(f"Portfolio {name} already exists, returning existing entity")
                return existing_portfolio
            
            # Step 2: Create new entity if not found
            logger.info(f"Creating new portfolio: {name}")
            
            # Handle defaults
            portfolio_type = kwargs.get('portfolio_type', "STANDARD")
            initial_cash = kwargs.get('initial_cash', 100000.0)
            currency = kwargs.get('currency', "USD")
            owner_id = kwargs.get('owner_id')
            inception_date = kwargs.get('inception_date', date.today())
            created_at = kwargs.get('created_at', datetime.now())
            
            # Import and handle enum
            from src.domain.entities.finance.portfolio.portfolio import PortfolioType
            portfolio_type_enum = PortfolioType.STANDARD
            try:
                portfolio_type_enum = PortfolioType(portfolio_type)
            except ValueError:
                logger.warning(f"Invalid portfolio type {portfolio_type}, using STANDARD")
                pass
            
            # Create domain entity
            new_portfolio = PortfolioEntity(
                name=name,
                portfolio_type=portfolio_type_enum,
                initial_cash=Decimal(str(initial_cash)),
                currency=currency,
                owner_id=owner_id,
                inception_date=inception_date,
                created_at=created_at
            )
            
            # Step 3: Convert to ORM model and persist
            portfolio_model = self.mapper.to_orm(new_portfolio)
            
            self.session.add(portfolio_model)
            self.session.commit()
            
            # Step 4: Convert back to domain entity with database ID
            persisted_entity = self.mapper.to_domain(portfolio_model)
            
            logger.info(f"Successfully created portfolio {name} with ID {persisted_entity.id}")
            return persisted_entity
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating/getting portfolio {name}: {str(e)}")
            raise
    
    # Standard CRUD interface
    def create(self, entity: PortfolioEntity) -> PortfolioEntity:
        """Create new portfolio entity in database (standard CRUD interface)."""
        return self.add(entity)