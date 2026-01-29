

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from decimal import Decimal


from ...base_repository import BaseLocalRepository, EntityType, ModelType
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset
from sqlalchemy.orm import Session

class FinancialAssetRepository(BaseLocalRepository[EntityType, ModelType], ABC):
    """
    Base repository for all financial asset types (shares, bonds, currencies, etc.).
    Extends BaseRepository with financial asset specific functionality.
    """
    def __init__(self, session: Session,**kwargs):
        """Initialize IndexRepository with database session."""

        super().__init__(session)
        self.factory = kwargs.get('factory')
        from application.services.api_service.ibkr_service.market_data import MarketData
        self.market_data = MarketData()
    @property
    def entity_class(self):
        
        return FinancialAsset
    # --- Financial Asset Specific Methods ---

    def get_by_ticker(self, ticker: str) -> Optional[EntityType]:
        """Get financial asset by ticker symbol."""
        try:
            model = self.session.query(self.model_class).filter(
                self.model_class.ticker == ticker
            ).first()
            return self._to_entity(model) if model else None
        except Exception as e:
            print(f"Error retrieving {self.model_class.__name__} by ticker {ticker}: {e}")
            return None

    def exists_by_ticker(self, ticker: str) -> bool:
        """Check if financial asset exists by ticker."""
        try:
            return self.session.query(self.model_class).filter(
                self.model_class.ticker == ticker
            ).first() is not None
        except Exception as e:
            print(f"Error checking existence by ticker {ticker}: {e}")
            return False

    def get_by_exchange(self, exchange_id: int) -> List[EntityType]:
        """Get all financial assets for a specific exchange."""
        try:
            models = self.session.query(self.model_class).filter(
                self.model_class.exchange_id == exchange_id
            ).all()
            return [self._to_entity(model) for model in models]
        except Exception as e:
            print(f"Error retrieving {self.model_class.__name__} by exchange {exchange_id}: {e}")
            return []

    def add_bulk(self, entities: List[EntityType]) -> List[EntityType]:
        """Add multiple financial assets in a single transaction."""
        try:
            # Convert to models and assign sequential IDs if needed
            models = []
            next_id = self._get_next_available_id()
            
            for i, entity in enumerate(entities):
                if not hasattr(entity, 'id') or entity.id is None:
                    entity.id = next_id + i
                
                # For company shares, ensure company_id matches entity id
                if hasattr(entity, 'company_id') and (not entity.company_id or entity.company_id is None):
                    entity.company_id = entity.id
                
                models.append(self._to_model(entity))
            
            # Add all models
            self.session.add_all(models)
            self.session.commit()
            
            # Refresh all models and convert back to entities
            for model in models:
                self.session.refresh(model)
            
            return [self._to_entity(model) for model in models]
            
        except Exception as e:
            self.session.rollback()
            print(f"Error in bulk add operation: {e}")
            raise

    def _get_next_available_financial_asset_id(self) -> int:
        """
        Get the next available ID for financial asset creation.
        Specific implementation for financial assets with proper error handling.
        """
        return self._get_next_available_id()

    # --- Market Data and Analysis Methods ---

    def get_active_assets(self) -> List[EntityType]:
        """Get all currently active financial assets (no end date or future end date)."""
        try:
            from datetime import datetime
            today = datetime.now().date()
            
            models = self.session.query(self.model_class).filter(
                (self.model_class.end_date.is_(None)) | 
                (self.model_class.end_date > today)
            ).all()
            
            return [self._to_entity(model) for model in models]
        except Exception as e:
            print(f"Error retrieving active {self.model_class.__name__}: {e}")
            return []

    def get_assets_by_date_range(self, start_date, end_date) -> List[EntityType]:
        """Get assets active within a specific date range."""
        try:
            models = self.session.query(self.model_class).filter(
                self.model_class.start_date <= end_date,
                (self.model_class.end_date.is_(None)) | 
                (self.model_class.end_date >= start_date)
            ).all()
            
            return [self._to_entity(model) for model in models]
        except Exception as e:
            print(f"Error retrieving {self.model_class.__name__} by date range: {e}")
            return []

    def get_or_create(self, ticker: str, name: Optional[str] = None, exchange_id: Optional[int] = None, 
                      currency_id: Optional[int] = None, **kwargs) -> Optional[EntityType]:
        """
        Get or create a financial asset with dependency resolution.
        
        Args:
            ticker: Financial asset ticker symbol (primary identifier)
            name: Financial asset name (optional, defaults to ticker if not provided)
            exchange_id: Exchange ID (optional, will use default if not provided)
            currency_id: Currency ID (optional, will use default USD if not provided)
            **kwargs: Additional fields specific to the financial asset type
            
        Returns:
            Domain financial asset entity or None if creation failed
        """
        try:
            # First try to get existing asset by ticker
            existing = self.get_by_ticker(ticker)
            if existing:
                return existing
            
            # Resolve dependencies
            # Get or create exchange dependency if not provided
            if not exchange_id:
                exchange_local_repo = self.factory.exchange_local_repo
                default_exchange = exchange_local_repo.get_or_create("NYSE", "New York Stock Exchange")
                exchange_id = default_exchange.id if default_exchange else 1
            
            # Get or create currency dependency if not provided
            if not currency_id:
                currency_local_repo = self.factory.currency_local_repo
                default_currency = currency_local_repo.get_or_create("USD", "United States Dollar")
                currency_id = default_currency.id if default_currency else 1
            
            # Set defaults
            from datetime import datetime
            
            # Get next available ID
            next_id = self._get_next_available_id()
            
            # Create entity data
            entity_data = {
                'id': next_id,
                'ticker': ticker,
                'name': name or ticker,
                'exchange_id': exchange_id,
                'currency_id': currency_id,
                'start_date': datetime.now().date(),
                'end_date': None
            }
            
            # Add any additional kwargs
            entity_data.update(kwargs)
            
            # Create new entity using the specific entity class
            new_entity = self.entity_class(**entity_data)
            
            # Add to database
            return self.add(new_entity)
            
        except Exception as e:
            print(f"Error in get_or_create for financial asset {ticker}: {e}")
            return None
        
    