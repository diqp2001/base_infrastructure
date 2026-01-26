# ETF Share Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/etf_share.py
from typing import Optional
from sqlalchemy.orm import Session

from src.domain.ports.finance.financial_assets.share.etf_share_port import ETFSharePort
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.infrastructure.models.finance.financial_assets.etf_share import ETFShareModel as ETFShareModel
from src.domain.entities.finance.financial_assets.share.etf_share import ETFShare as ETFShareEntity
from src.infrastructure.repositories.mappers.finance.financial_assets.etf_share_mapper import ETFShareMapper
class ETFShareRepository(FinancialAssetRepository, ETFSharePort):
    """Local repository for ETF share model"""
    
    def __init__(self, session: Session, factory, mapper: ETFShareMapper = None):
        """Initialize ETFShareRepository with database session."""
        super().__init__(session)
        self.factory = factory
        self.data_store = []
        self.mapper = mapper or ETFShareMapper()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for ETFShare."""
        return ETFShareModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for ETFShare."""
        return ETFShareEntity
    
    def save(self, etf_share):
        """Save ETF share to local storage"""
        self.data_store.append(etf_share)
        
    def find_by_id(self, etf_share_id):
        """Find ETF share by ID"""
        for etf_share in self.data_store:
            if getattr(etf_share, 'id', None) == etf_share_id:
                return etf_share
        return None
        
    def find_all(self):
        """Find all ETF shares"""
        return self.data_store.copy()
    
    def get_by_ticker(self, ticker: str):
        """Get ETF share by ticker symbol."""
        try:
            model = self.session.query(self.model_class).filter(
                self.model_class.ticker == ticker
            ).first()
            return self._to_entity(model) if model else None
        except Exception as e:
            print(f"Error retrieving ETF share by ticker {ticker}: {e}")
            return None
    
    def get_or_create(self, ticker: str, name: str = None, exchange_id: int = None) -> Optional[ETFShareEntity]:
        """
        Get or create an ETF share by ticker with dependency resolution.
        
        Args:
            ticker: ETF ticker symbol (e.g., 'SPY', 'QQQ')
            name: ETF name (optional, will default if not provided)
            exchange_id: Exchange ID (optional, will use default if not provided)
            
        Returns:
            ETFShare entity or None if creation failed
        """
        try:
            # First try to get existing ETF share
            existing = self.get_by_ticker(ticker)
            if existing:
                return existing
            
            # Create new ETF share if it doesn't exist
            print(f"Creating new ETF share: {ticker}")
            
            # Set default values
            if not name:
                name = f"ETF {ticker.upper()}"
            
            if not exchange_id:
                # Get or create a default exchange
                exchange_local_repo = self.factory.exchange_local_repo
                default_exchange = exchange_local_repo.get_or_create("NASDAQ", name="NASDAQ")
                exchange_id = default_exchange.id if default_exchange else 1
            
            new_etf_share = ETFShareEntity(
                id=None,
                name=name,
                symbol=ticker.upper(),
                exchange_id=exchange_id
            )
            
            return self.add(new_etf_share)
            
        except Exception as e:
            print(f"Error in get_or_create for ETF share {ticker}: {e}")
            return None
    
    def add(self, etf_share: ETFShareEntity) -> ETFShareEntity:
        """Add a new ETF share to the database."""
        try:
            model = self._to_model(etf_share)
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)
            return self._to_entity(model)
        except Exception as e:
            self.session.rollback()
            print(f"Error adding ETF share: {e}")
            return None
    
    def _to_entity(self, model: ETFShareModel) -> ETFShareEntity:
        """Convert model to entity."""
        if not model:
            return None
        return self.mapper.to_domain(model)
        )
    
    def _to_model(self, entity: ETFShareEntity) -> ETFShareModel:
        """Convert entity to model."""
        if not entity:
            return None
        return self.mapper.to_orm(entity)