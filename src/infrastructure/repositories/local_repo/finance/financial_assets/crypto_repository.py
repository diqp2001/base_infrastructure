"""
Crypto Repository - handles CRUD operations for Crypto entities.

Follows the standardized repository pattern with _create_or_get_* methods
consistent with other repositories in the codebase.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from decimal import Decimal

from src.infrastructure.models.finance.financial_assets.crypto import Crypto as CryptoModel
from src.domain.entities.finance.financial_assets.crypto import Crypto as CryptoEntity
from infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.domain.ports.finance.financial_assets.crypto_port import CryptoPort


class CryptoRepository(FinancialAssetRepository, CryptoPort):
    """Repository for managing Crypto entities."""
    
    def __init__(self, session: Session):
        super().__init__(session)
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Crypto."""
        return CryptoModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Crypto."""
        return CryptoEntity
    
    def _to_entity(self, model: CryptoModel) -> CryptoEntity:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        
        return CryptoEntity(
            asset_id=model.id,  # Using model.id as asset_id for compatibility
            symbol=model.symbol,
            name=model.name
        )
    
    def _to_model(self, entity: CryptoEntity) -> CryptoModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        
        return CryptoModel(
            symbol=entity.symbol,
            name=entity.name,
            current_price=0,
            is_active=True,
            is_tradeable=True,
            last_update=datetime.now()
        )
    
    def get_all(self) -> List[CryptoEntity]:
        """Retrieve all Crypto records."""
        models = self.session.query(CryptoModel).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_id(self, crypto_id: int) -> Optional[CryptoEntity]:
        """Retrieve Crypto by its ID."""
        model = self.session.query(CryptoModel).filter(
            CryptoModel.id == crypto_id
        ).first()
        return self._to_entity(model)
    
    def get_by_symbol(self, symbol: str) -> Optional[CryptoEntity]:
        """Retrieve Crypto by symbol."""
        model = self.session.query(CryptoModel).filter(
            CryptoModel.symbol == symbol.upper()
        ).first()
        return self._to_entity(model)
    
    def get_by_name(self, name: str) -> Optional[CryptoEntity]:
        """Retrieve Crypto by name."""
        model = self.session.query(CryptoModel).filter(
            CryptoModel.name == name
        ).first()
        return self._to_entity(model)
    
    def get_stakeable_cryptos(self) -> List[CryptoEntity]:
        """Retrieve all stakeable cryptocurrencies."""
        models = self.session.query(CryptoModel).filter(
            CryptoModel.is_stakeable == True,
            CryptoModel.is_active == True
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_active_cryptos(self) -> List[CryptoEntity]:
        """Retrieve all active cryptocurrencies."""
        models = self.session.query(CryptoModel).filter(
            CryptoModel.is_active == True
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_blockchain(self, blockchain: str) -> List[CryptoEntity]:
        """Retrieve cryptocurrencies by blockchain."""
        models = self.session.query(CryptoModel).filter(
            CryptoModel.blockchain == blockchain
        ).all()
        return [self._to_entity(model) for model in models]
    
    def exists_by_symbol(self, symbol: str) -> bool:
        """Check if a Crypto exists by symbol."""
        return self.session.query(CryptoModel).filter(
            CryptoModel.symbol == symbol.upper()
        ).first() is not None
    
    def add(self, entity: CryptoEntity) -> CryptoEntity:
        """Add a new Crypto entity to the database."""
        # Check for existing crypto with same symbol
        if self.exists_by_symbol(entity.symbol):
            existing = self.get_by_symbol(entity.symbol)
            return existing
        
        model = self._to_model(entity)
        self.session.add(model)
        self.session.commit()
        
        return self._to_entity(model)
    
    def update(self, crypto_id: int, **kwargs) -> Optional[CryptoEntity]:
        """Update an existing Crypto record."""
        model = self.session.query(CryptoModel).filter(
            CryptoModel.id == crypto_id
        ).first()
        
        if not model:
            return None
        
        for attr, value in kwargs.items():
            if hasattr(model, attr):
                setattr(model, attr, value)
        
        model.last_update = datetime.now()
        self.session.commit()
        return self._to_entity(model)
    
    def update_price(self, symbol: str, price: float, **market_data) -> Optional[CryptoEntity]:
        """Update crypto price and market data."""
        model = self.session.query(CryptoModel).filter(
            CryptoModel.symbol == symbol.upper()
        ).first()
        
        if not model:
            return None
        
        model.current_price = price
        model.last_update = datetime.now()
        
        # Update additional market data if provided
        for field, value in market_data.items():
            if hasattr(model, field):
                setattr(model, field, value)
        
        self.session.commit()
        return self._to_entity(model)
    
    def delete(self, crypto_id: int) -> bool:
        """Delete a Crypto record by ID."""
        model = self.session.query(CryptoModel).filter(
            CryptoModel.id == crypto_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        self.session.commit()
        return True
    
    def _get_next_available_crypto_id(self) -> int:
        """
        Get the next available ID for crypto creation.
        Returns the next sequential ID based on existing database records.
        
        Returns:
            int: Next available ID (defaults to 1 if no records exist)
        """
        try:
            max_id_result = self.session.query(CryptoModel.id).order_by(CryptoModel.id.desc()).first()
            
            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist
                
        except Exception as e:
            print(f"Warning: Could not determine next available crypto ID: {str(e)}")
            return 1  # Default to 1 if query fails
    
    def _create_or_get_crypto(self, symbol: str, name: str, blockchain: str = None,
                             **kwargs) -> CryptoEntity:
        """
        Create crypto entity if it doesn't exist, otherwise return existing.
        Follows the same pattern as other repositories' _create_or_get_* methods.
        
        Args:
            symbol: Crypto symbol (unique identifier)
            name: Crypto name
            blockchain: Blockchain network
            **kwargs: Additional fields for the crypto model
            
        Returns:
            CryptoEntity: Created or existing crypto
        """
        # Check if entity already exists by symbol (unique identifier)
        if self.exists_by_symbol(symbol):
            return self.get_by_symbol(symbol)
        
        try:
            # Get next available ID
            next_id = self._get_next_available_crypto_id()
            
            # Create new crypto entity
            crypto = CryptoEntity(
                asset_id=next_id,
                symbol=symbol.upper(),
                name=name
            )
            
            # Add to database
            return self.add(crypto)
            
        except Exception as e:
            print(f"Error creating crypto {symbol}: {str(e)}")
            return None
    
    def get_market_cap_leaders(self, limit: int = 10) -> List[CryptoEntity]:
        """Get cryptocurrencies by market cap (descending)."""
        models = self.session.query(CryptoModel).filter(
            CryptoModel.is_active == True,
            CryptoModel.market_cap.isnot(None)
        ).order_by(CryptoModel.market_cap.desc()).limit(limit).all()
        
        return [self._to_entity(model) for model in models]
    
    def get_high_volume_cryptos(self, min_volume_24h: float = 1000000) -> List[CryptoEntity]:
        """Get cryptocurrencies with high trading volume."""
        models = self.session.query(CryptoModel).filter(
            CryptoModel.is_active == True,
            CryptoModel.volume_24h >= min_volume_24h
        ).order_by(CryptoModel.volume_24h.desc()).all()
        
        return [self._to_entity(model) for model in models]
    
    # Standard CRUD interface
    def create(self, entity: CryptoEntity) -> CryptoEntity:
        """Create new crypto entity in database (standard CRUD interface)."""
        return self.add(entity)