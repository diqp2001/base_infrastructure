# Swap Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/swap/swap.py
from typing import Optional
from sqlalchemy.orm import Session

from src.domain.ports.finance.financial_assets.derivatives.swap_port import SwapPort
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.infrastructure.models.finance.financial_assets.derivative.swap.swap import SwapModel as SwapModel
from src.domain.entities.finance.financial_assets.derivatives.swap import Swap as SwapEntity

class SwapRepository(FinancialAssetRepository, SwapPort):
    """Local repository for swap model"""
    
    def __init__(self, session: Session, factory):
        """Initialize SwapRepository with database session."""
        super().__init__(session, factory)
        self.data_store = []
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Swap."""
        return SwapModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Swap."""
        return SwapEntity
    
    def save(self, swap):
        """Save swap to local storage"""
        self.data_store.append(swap)
        
    def find_by_id(self, swap_id):
        """Find swap by ID"""
        for swap in self.data_store:
            if getattr(swap, 'id', None) == swap_id:
                return swap
        return None
        
    def find_all(self):
        """Find all swaps"""
        return self.data_store.copy()
    
    def get_by_symbol(self, symbol: str) -> Optional[SwapEntity]:
        """Get swap by symbol."""
        try:
            model = self.session.query(self.model_class).filter(
                self.model_class.symbol == symbol
            ).first()
            return self._to_entity(model) if model else None
        except Exception as e:
            print(f"Error retrieving swap by symbol {symbol}: {e}")
            return None
    
    def get_or_create(self, symbol: str, name: str = None, currency_id: int = None, 
                      underlying_asset_id: int = None, **kwargs) -> Optional[SwapEntity]:
        """
        Get or create a swap by symbol with dependency resolution.
        
        Args:
            symbol: Swap identifier/symbol
            name: Swap name (optional, will default if not provided)
            currency_id: Currency ID (optional, will use default if not provided)
            underlying_asset_id: Underlying asset ID (optional)
            **kwargs: Additional fields for the swap
            
        Returns:
            Swap entity or None if creation failed
        """
        try:
            # First try to get existing swap
            existing = self.get_by_symbol(symbol)
            if existing:
                return existing
            
            # Create new swap if it doesn't exist
            print(f"Creating new swap: {symbol}")
            
            if not name:
                name = f"Swap {symbol.upper()}"
            
            if not currency_id:
                # Get or create a default currency
                currency_local_repo = self.factory.currency_local_repo
                default_currency = currency_local_repo.get_or_create(iso_code="USD")
                currency_id = default_currency.asset_id if default_currency else 1
            
            new_swap = SwapEntity(
                id=None,
                name=name,
                symbol=symbol.upper(),
                currency_id=currency_id,
                underlying_asset_id=underlying_asset_id
            )
            
            return self.add(new_swap)
            
        except Exception as e:
            print(f"Error in get_or_create for swap {symbol}: {e}")
            return None
    
    def add(self, swap: SwapEntity) -> SwapEntity:
        """Add a new swap to the database."""
        try:
            model = self._to_model(swap)
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)
            return self._to_entity(model)
        except Exception as e:
            self.session.rollback()
            print(f"Error adding swap: {e}")
            return None
    
    def _to_entity(self, model: SwapModel) -> SwapEntity:
        """Convert model to entity."""
        if not model:
            return None
        return SwapEntity(
            id=model.id,
            name=model.name,
            symbol=model.symbol,
            currency_id=getattr(model, 'currency_id', None),
            underlying_asset_id=getattr(model, 'underlying_asset_id', None)
        )
    
    def _to_model(self, entity: SwapEntity) -> SwapModel:
        """Convert entity to model."""
        return SwapModel(
            id=entity.id,
            name=entity.name,
            symbol=entity.symbol,
            currency_id=entity.currency_id,
            underlying_asset_id=entity.underlying_asset_id
        )