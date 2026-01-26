# Security Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/security.py

from typing import Optional
from src.domain.ports.finance.financial_assets.security_port import SecurityPort
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.infrastructure.models.finance.financial_assets.security import SecurityModel as SecurityModel
from src.domain.entities.finance.financial_assets.security import Security as SecurityEntity
from sqlalchemy.orm import Session


class SecurityRepository(FinancialAssetRepository, SecurityPort):
    """Local repository for security model"""
    
    def __init__(self, session: Session, factory):
        """Initialize SecurityRepository with database session."""
        super().__init__(session)
        self.factory = factory
        self.data_store = []
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Security."""
        return SecurityModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Security."""
        return SecurityEntity
        
    
    def save(self, security):
        """Save security to local storage"""
        self.data_store.append(security)
        
    def find_by_id(self, security_id):
        """Find security by ID"""
        for security in self.data_store:
            if getattr(security, 'id', None) == security_id:
                return security
        return None
        
    def find_all(self):
        """Find all securities"""
        return self.data_store.copy()
    
    def get_by_symbol(self, symbol: str) -> Optional[SecurityEntity]:
        """Get security by symbol."""
        try:
            model = self.session.query(self.model_class).filter(
                self.model_class.symbol == symbol
            ).first()
            return self._to_entity(model) if model else None
        except Exception as e:
            print(f"Error retrieving security by symbol {symbol}: {e}")
            return None
    
    def get_by_isin(self, isin: str) -> Optional[SecurityEntity]:
        """Get security by ISIN."""
        try:
            model = self.session.query(self.model_class).filter(
                self.model_class.isin == isin
            ).first()
            return self._to_entity(model) if model else None
        except Exception as e:
            print(f"Error retrieving security by ISIN {isin}: {e}")
            return None
    
    def get_or_create(self, symbol: str = None, isin: str = None, name: str = None, 
                      portfolio_id: int = None, **kwargs) -> Optional[SecurityEntity]:
        """
        Get or create a security by symbol or ISIN with dependency resolution.
        
        Args:
            symbol: Security symbol/ticker
            isin: International Securities Identification Number
            name: Security name (optional, will default if not provided)
            portfolio_id: Portfolio ID (optional)
            **kwargs: Additional fields for the security
            
        Returns:
            Security entity or None if creation failed
        """
        try:
            # First try to get existing security by symbol or ISIN
            if symbol:
                existing = self.get_by_symbol(symbol)
                if existing:
                    return existing
            
            if isin:
                existing = self.get_by_isin(isin)
                if existing:
                    return existing
            
            # Create new security if it doesn't exist
            identifier = symbol or isin or "UNK"
            if not name:
                name = f"Security {identifier.upper()}"
            
            new_security = SecurityEntity(
                id=None,
                name=name,
                symbol=symbol or identifier.upper(),
                portfolio_id=portfolio_id
            )
            
            return self.add(new_security)
            
        except Exception as e:
            print(f"Error in get_or_create for security {symbol or isin}: {e}")
            return None
    
    def add(self, security: SecurityEntity) -> SecurityEntity:
        """Add a new security to the database."""
        try:
            model = self._to_model(security)
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)
            return self._to_entity(model)
        except Exception as e:
            self.session.rollback()
            print(f"Error adding security: {e}")
            return None
    
    def _to_entity(self, model: SecurityModel) -> SecurityEntity:
        """Convert model to entity."""
        if not model:
            return None
        return SecurityEntity(
            id=model.id,
            name=model.name,
            symbol=model.symbol,
            portfolio_id=getattr(model, 'portfolio_id', None)
        )
    
    def _to_model(self, entity: SecurityEntity) -> SecurityModel:
        """Convert entity to model."""
        return SecurityModel(
            id=entity.id,
            name=entity.name,
            symbol=entity.symbol,
            portfolio_id=entity.portfolio_id
        )