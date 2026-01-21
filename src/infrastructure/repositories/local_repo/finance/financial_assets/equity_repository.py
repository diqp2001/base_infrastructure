# Equity Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/equity.py

from typing import Optional
from infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.domain.ports.finance.financial_assets.equity_port import EquityPort
from src.infrastructure.models.finance.financial_assets.equity import EquityModel as EquityModel
from src.domain.entities.finance.financial_assets.equity import Equity as EquityEntity
from sqlalchemy.orm import Session
class EquityRepository(FinancialAssetRepository, EquityPort):
    """Local repository for equity model"""
    
    def __init__(self, session: Session, factory):
        """Initialize EquityRepository with database session."""
        super().__init__(session)
        self.factory = factory
        self.data_store = []
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Equity."""
        return EquityModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Equity."""
        return EquityEntity
    
    def save(self, equity):
        """Save equity to local storage"""
        self.data_store.append(equity)
        
    def find_by_id(self, equity_id):
        """Find equity by ID"""
        for equity in self.data_store:
            if getattr(equity, 'id', None) == equity_id:
                return equity
        return None
        
    def find_all(self):
        """Find all equities"""
        return self.data_store.copy()
    
    def get_by_symbol(self, symbol: str) -> Optional[EquityEntity]:
        """Get equity by symbol."""
        try:
            model = self.session.query(self.model_class).filter(
                self.model_class.symbol == symbol
            ).first()
            return self._to_entity(model) if model else None
        except Exception as e:
            print(f"Error retrieving equity by symbol {symbol}: {e}")
            return None
    
    def get_or_create(self, symbol: str, name: str = None, **kwargs) -> Optional[EquityEntity]:
        """
        Get or create an equity by symbol with dependency resolution.
        
        Args:
            symbol: Equity symbol/ticker
            name: Equity name (optional, will default if not provided)
            **kwargs: Additional fields for the equity
            
        Returns:
            Equity entity or None if creation failed
        """
        try:
            # First try to get existing equity
            existing = self.get_by_symbol(symbol)
            if existing:
                return existing
            
            # Create new equity if it doesn't exist
            print(f"Creating new equity: {symbol}")
            
            if not name:
                name = f"Equity {symbol.upper()}"
            
            new_equity = EquityEntity(
                id=None,
                name=name,
                symbol=symbol.upper()
            )
            
            return self.add(new_equity)
            
        except Exception as e:
            print(f"Error in get_or_create for equity {symbol}: {e}")
            return None
    
    def add(self, equity: EquityEntity) -> EquityEntity:
        """Add a new equity to the database."""
        try:
            model = self._to_model(equity)
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)
            return self._to_entity(model)
        except Exception as e:
            self.session.rollback()
            print(f"Error adding equity: {e}")
            return None
    
    def _to_entity(self, model: EquityModel) -> EquityEntity:
        """Convert model to entity."""
        if not model:
            return None
        return EquityEntity(
            id=model.id,
            name=model.name,
            symbol=model.symbol
        )
    
    def _to_model(self, entity: EquityEntity) -> EquityModel:
        """Convert entity to model."""
        return EquityModel(
            id=entity.id,
            name=entity.name,
            symbol=entity.symbol
        )