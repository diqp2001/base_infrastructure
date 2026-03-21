"""
Account Repository - handles CRUD operations for Account entities.

Follows the standardized repository pattern with _create_or_get_* methods
consistent with other repositories in the codebase.
"""

import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src.infrastructure.models.finance.account import AccountModel
from src.domain.entities.finance.account import Account as AccountEntity
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.finance.account_mapper import AccountMapper
from src.domain.ports.finance.account_port import AccountPort

logger = logging.getLogger(__name__)


class AccountRepository(BaseLocalRepository, AccountPort):
    """Repository for managing Account entities."""
    
    def __init__(self, session: Session, factory, mapper: AccountMapper = None):
        """Initialize AccountRepository with database session and mapper."""
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or AccountMapper()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Account."""
        return AccountModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Account."""
        return AccountEntity
    
    def _to_entity(self, model: AccountModel) -> AccountEntity:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        return self.mapper.to_domain(model)
    
    def _to_model(self, entity: AccountEntity) -> AccountModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        return self.mapper.to_orm(entity)
    
    def get_all(self) -> List[AccountEntity]:
        """Retrieve all Account records."""
        models = self.session.query(AccountModel).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_id(self, account_id: int) -> Optional[AccountEntity]:
        """Retrieve an Account by its ID."""
        model = self.session.query(AccountModel).filter(
            AccountModel.id == account_id
        ).first()
        return self._to_entity(model)
    
    def get_by_account_id(self, account_id: str) -> Optional[AccountEntity]:
        """Retrieve an Account by its account_id."""
        model = self.session.query(AccountModel).filter(
            AccountModel.account_id == account_id
        ).first()
        return self._to_entity(model)
    
    def add(self, entity: AccountEntity) -> Optional[AccountEntity]:
        """Add a new Account entity to the database."""
        try:
            # Check for existing account with same account_id
            existing = self.get_by_account_id(entity.account_id)
            if existing:
                return existing
            
            model = self._to_model(entity)
            self.session.add(model)
            self.session.commit()
            
            return self._to_entity(model)
        except Exception as e:
            logger.error(f"Error adding account {entity.account_id}: {e}")
            self.session.rollback()
            return None
    
    def update(self, entity: AccountEntity) -> Optional[AccountEntity]:
        """Update an existing Account record."""
        try:
            model = self.session.query(AccountModel).filter(
                AccountModel.id == entity.id
            ).first()
            
            if not model:
                return None
            
            # Update model with entity data
            updated_model = self.mapper.to_orm(entity, model)
            self.session.commit()
            return self._to_entity(updated_model)
        except Exception as e:
            logger.error(f"Error updating account {entity.id}: {e}")
            self.session.rollback()
            return None
    
    def delete(self, account_id: int) -> bool:
        """Delete an Account record by ID."""
        try:
            model = self.session.query(AccountModel).filter(
                AccountModel.id == account_id
            ).first()
            
            if not model:
                return False
            
            self.session.delete(model)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting account {account_id}: {e}")
            self.session.rollback()
            return False
    
    def _create_or_get(self, account_id: str, **kwargs) -> Optional[AccountEntity]:
        """
        Create account entity if it doesn't exist, otherwise return existing.
        
        Args:
            account_id: Account identifier (unique)
            **kwargs: Additional account parameters
            
        Returns:
            AccountEntity: Created or existing account
        """
        try:
            # Check if entity already exists by account_id
            existing = self.get_by_account_id(account_id)
            if existing:
                return existing
            
            # Get next available ID
            next_id = self._get_next_available_id()
            
            # Create new account entity
            from src.domain.entities.finance.account import AccountType, AccountStatus
            
            account = AccountEntity(
                id=next_id,
                account_id=account_id,
                account_type=kwargs.get('account_type', AccountType.CASH),
                status=kwargs.get('status', AccountStatus.ACTIVE),
                base_currency_id=kwargs.get('base_currency_id', 1),  # Default to USD
                created_at=kwargs.get('created_at', datetime.now())
            )
            
            # Add to database
            return self.add(account)
            
        except Exception as e:
            logger.error(f"Error creating account {account_id}: {e}")
            return None