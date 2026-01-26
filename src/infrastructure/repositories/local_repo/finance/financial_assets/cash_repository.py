"""
Cash Repository - handles CRUD operations for Cash entities.

Follows the standardized repository pattern with _create_or_get_* methods
consistent with other repositories in the codebase.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from decimal import Decimal

from src.infrastructure.models.finance.financial_assets.cash import CashModel as CashModel
from src.domain.entities.finance.financial_assets.cash import Cash as CashEntity
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.domain.ports.finance.financial_assets.cash_port import CashPort


class CashRepository(FinancialAssetRepository, CashPort):
    """Repository for managing Cash entities."""
    
    def __init__(self, session: Session, factory):
        """Initialize CashRepository with database session."""
        super().__init__(session)
        self.factory = factory
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Cash."""
        return CashModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Cash."""
        return CashEntity
    
    def _to_entity(self, model: CashModel) -> CashEntity:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        
        return CashEntity(
            asset_id=model.asset_id,
            name=model.name,
            amount=float(model.amount) if model.amount else 0.0,
            currency=model.currency or "USD"
        )
    
    def _to_model(self, entity: CashEntity) -> CashModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        
        return CashModel(
            asset_id=entity.asset_id,
            name=entity.name,
            amount=float(entity.amount),
            currency=entity.currency,
            last_updated=datetime.now()
        )
    
    def get_all(self) -> List[CashEntity]:
        """Retrieve all Cash records."""
        models = self.session.query(CashModel).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_id(self, cash_id: int) -> Optional[CashEntity]:
        """Retrieve Cash by its ID."""
        model = self.session.query(CashModel).filter(
            CashModel.id == cash_id
        ).first()
        return self._to_entity(model)
    
    def get_by_asset_id(self, asset_id: int) -> Optional[CashEntity]:
        """Retrieve Cash by asset ID."""
        model = self.session.query(CashModel).filter(
            CashModel.asset_id == asset_id
        ).first()
        return self._to_entity(model)
    
    def get_by_currency(self, currency: str) -> List[CashEntity]:
        """Retrieve all cash holdings by currency."""
        models = self.session.query(CashModel).filter(
            CashModel.currency == currency
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_available_cash(self) -> List[CashEntity]:
        """Retrieve all available (non-locked) cash holdings."""
        models = self.session.query(CashModel).filter(
            CashModel.is_available == True,
            CashModel.is_locked == False
        ).all()
        return [self._to_entity(model) for model in models]
    
    def exists_by_asset_id(self, asset_id: int) -> bool:
        """Check if a Cash exists by asset ID."""
        return self.session.query(CashModel).filter(
            CashModel.asset_id == asset_id
        ).first() is not None
    
    def add(self, entity: CashEntity) -> CashEntity:
        """Add a new Cash entity to the database."""
        # Check for existing cash with same asset_id
        if self.exists_by_asset_id(entity.asset_id):
            existing = self.get_by_asset_id(entity.asset_id)
            return existing
        
        model = self._to_model(entity)
        self.session.add(model)
        self.session.commit()
        
        return self._to_entity(model)
    
    def update(self, cash_id: int, **kwargs) -> Optional[CashEntity]:
        """Update an existing Cash record."""
        model = self.session.query(CashModel).filter(
            CashModel.id == cash_id
        ).first()
        
        if not model:
            return None
        
        for attr, value in kwargs.items():
            if hasattr(model, attr):
                setattr(model, attr, value)
        
        model.last_updated = datetime.now()
        self.session.commit()
        return self._to_entity(model)
    
    def update_amount(self, asset_id: int, new_amount: float) -> Optional[CashEntity]:
        """Update the amount of a cash holding."""
        model = self.session.query(CashModel).filter(
            CashModel.asset_id == asset_id
        ).first()
        
        if not model:
            return None
        
        model.amount = new_amount
        model.last_updated = datetime.now()
        self.session.commit()
        return self._to_entity(model)
    
    def delete(self, cash_id: int) -> bool:
        """Delete a Cash record by ID."""
        model = self.session.query(CashModel).filter(
            CashModel.id == cash_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        self.session.commit()
        return True
    
    def _get_next_available_asset_id(self) -> int:
        """
        Get the next available asset ID for cash creation.
        Returns the next sequential ID based on existing database records.
        
        Returns:
            int: Next available asset ID (defaults to 1 if no records exist)
        """
        try:
            max_id_result = self.session.query(CashModel.asset_id).order_by(CashModel.asset_id.desc()).first()
            
            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist
                
        except Exception as e:
            print(f"Warning: Could not determine next available cash asset ID: {str(e)}")
            return 1  # Default to 1 if query fails
    
    def _create_or_get_cash(self, name: str, amount: float = 0.0, 
                           currency: str = "USD", **kwargs) -> CashEntity:
        """
        Create cash entity if it doesn't exist, otherwise return existing.
        Follows the same pattern as other repositories' _create_or_get_* methods.
        
        Args:
            name: Cash asset name
            amount: Cash amount
            currency: Currency code (ISO)
            **kwargs: Additional fields for the cash model
            
        Returns:
            CashEntity: Created or existing cash asset
        """
        # Get next available asset ID
        next_asset_id = self._get_next_available_asset_id()
        
        # Check if entity already exists by asset_id (unique identifier)
        if self.exists_by_asset_id(next_asset_id):
            return self.get_by_asset_id(next_asset_id)
        
        try:
            # Create new cash entity
            cash = CashEntity(
                asset_id=next_asset_id,
                name=name,
                amount=amount,
                currency=currency
            )
            
            # Add to database
            return self.add(cash)
            
        except Exception as e:
            print(f"Error creating cash asset {name}: {str(e)}")
            return None
    
    def get_total_by_currency(self, currency: str) -> Decimal:
        """Get total cash amount for a specific currency."""
        total = self.session.query(CashModel.amount).filter(
            CashModel.currency == currency,
            CashModel.is_available == True
        ).all()
        
        return sum(Decimal(str(amount[0])) for amount in total if amount[0])
    
    def get_or_create(self, name: str = None, currency: str = "USD", amount: float = 0.0, **kwargs) -> Optional[CashEntity]:
        """
        Get or create a cash asset by currency with dependency resolution.
        
        Args:
            name: Cash asset name (optional, will default if not provided)
            currency: Currency ISO code (e.g., 'USD', 'EUR')
            amount: Initial cash amount (default: 0.0)
            **kwargs: Additional fields for the cash
            
        Returns:
            Cash entity or None if creation failed
        """
        try:
            # First try to get existing cash by currency
            existing_cash = self.get_by_currency(currency)
            if existing_cash:
                # Return the first one found or the one with the most amount
                return max(existing_cash, key=lambda c: c.amount) if existing_cash else None
            
            # Create new cash if it doesn't exist
            if not name:
                name = f"Cash {currency.upper()}"
            
            # Get or create currency dependency
            currency_local_repo = self.factory.currency_local_repo
            currency_entity = currency_local_repo.get_or_create(iso_code=currency)
            
            return self._create_or_get_cash(name, amount, currency, **kwargs)
            
        except Exception as e:
            print(f"Error in get_or_create for cash {currency}: {e}")
            return None
    
    # Standard CRUD interface
    def create(self, entity: CashEntity) -> CashEntity:
        """Create new cash entity in database (standard CRUD interface)."""
        return self.add(entity)