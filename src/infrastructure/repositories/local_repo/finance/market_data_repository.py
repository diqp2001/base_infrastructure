"""
MarketData Repository - handles CRUD operations for MarketData entities.

Follows the standardized repository pattern with _create_or_get_* methods
consistent with other repositories in the codebase.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from decimal import Decimal

from src.infrastructure.models.finance.market_data import MarketDataModel
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.finance.market_data_mapper import MarketDataMapper


class MarketDataRepository(BaseLocalRepository):
    """Repository for managing MarketData entities."""
    
    def __init__(self, session: Session, factory, mapper: MarketDataMapper = None):
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or MarketDataMapper()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for MarketData."""
        return MarketDataModel
    
    def _to_entity(self, model: MarketDataModel):
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        return self.mapper.to_domain(model)
            'mid_price': Decimal(str(model.mid_price)) if model.mid_price else None,
            'spread': Decimal(str(model.spread)) if model.spread else None,
            'created_at': model.created_at
        }
    
    def _to_model(self, entity) -> MarketDataModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        return self.mapper.to_orm(entity)
            close=float(entity_data['close']) if entity_data.get('close') else None,
            exchange=entity_data.get('exchange'),
            last_trade_time=entity_data.get('last_trade_time'),
            mid_price=float(entity_data['mid_price']) if entity_data.get('mid_price') else None,
            spread=float(entity_data['spread']) if entity_data.get('spread') else None,
            created_at=entity_data.get('created_at', datetime.now())
        )
    
    def get_all(self) -> List[dict]:
        """Retrieve all MarketData records."""
        models = self.session.query(MarketDataModel).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_id(self, market_data_id: int) -> Optional[dict]:
        """Retrieve MarketData by its ID."""
        model = self.session.query(MarketDataModel).filter(
            MarketDataModel.id == market_data_id
        ).first()
        return self._to_entity(model)
    
    def get_by_symbol(self, symbol_ticker: str, symbol_exchange: str = None) -> List[dict]:
        """Retrieve market data by symbol."""
        query = self.session.query(MarketDataModel).filter(
            MarketDataModel.symbol_ticker == symbol_ticker
        )
        
        if symbol_exchange:
            query = query.filter(MarketDataModel.symbol_exchange == symbol_exchange)
        
        models = query.order_by(MarketDataModel.timestamp.desc()).all()
        return [self._to_entity(model) for model in models]
    
    def get_latest_by_symbol(self, symbol_ticker: str, symbol_exchange: str = None) -> Optional[dict]:
        """Retrieve the latest market data for a symbol."""
        query = self.session.query(MarketDataModel).filter(
            MarketDataModel.symbol_ticker == symbol_ticker
        )
        
        if symbol_exchange:
            query = query.filter(MarketDataModel.symbol_exchange == symbol_exchange)
        
        model = query.order_by(MarketDataModel.timestamp.desc()).first()
        return self._to_entity(model)
    
    def get_by_date_range(self, symbol_ticker: str, start_date: datetime, 
                         end_date: datetime, symbol_exchange: str = None) -> List[dict]:
        """Retrieve market data for a symbol within a date range."""
        query = self.session.query(MarketDataModel).filter(
            MarketDataModel.symbol_ticker == symbol_ticker,
            MarketDataModel.timestamp >= start_date,
            MarketDataModel.timestamp <= end_date
        )
        
        if symbol_exchange:
            query = query.filter(MarketDataModel.symbol_exchange == symbol_exchange)
        
        models = query.order_by(MarketDataModel.timestamp.asc()).all()
        return [self._to_entity(model) for model in models]
    
    def add(self, entity_data: dict) -> dict:
        """Add a new MarketData entity to the database."""
        model = self._to_model(entity_data)
        self.session.add(model)
        self.session.commit()
        
        return self._to_entity(model)
    
    def bulk_add(self, entity_data_list: List[dict]) -> List[dict]:
        """Add multiple MarketData entities to the database."""
        models = [self._to_model(data) for data in entity_data_list]
        self.session.bulk_save_objects(models)
        self.session.commit()
        
        return [self._to_entity(model) for model in models]
    
    def update(self, market_data_id: int, **kwargs) -> Optional[dict]:
        """Update an existing MarketData record."""
        model = self.session.query(MarketDataModel).filter(
            MarketDataModel.id == market_data_id
        ).first()
        
        if not model:
            return None
        
        for attr, value in kwargs.items():
            if hasattr(model, attr):
                setattr(model, attr, value)
        
        self.session.commit()
        return self._to_entity(model)
    
    def delete(self, market_data_id: int) -> bool:
        """Delete a MarketData record by ID."""
        model = self.session.query(MarketDataModel).filter(
            MarketDataModel.id == market_data_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        self.session.commit()
        return True
    
    def delete_old_data(self, symbol_ticker: str, days_to_keep: int = 30) -> int:
        """Delete old market data for a symbol, keeping only recent data."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        deleted_count = self.session.query(MarketDataModel).filter(
            MarketDataModel.symbol_ticker == symbol_ticker,
            MarketDataModel.timestamp < cutoff_date
        ).delete()
        
        self.session.commit()
        return deleted_count
    
    def _create_or_get_market_data(self, symbol_ticker: str, timestamp: datetime,
                                  price: float, symbol_exchange: str = "USA",
                                  security_type: str = "EQUITY", volume: int = None,
                                  **kwargs) -> dict:
        """
        Create market data entry if it doesn't exist, otherwise return existing.
        Follows the same pattern as other repositories' _create_or_get_* methods.
        
        Args:
            symbol_ticker: Stock ticker symbol
            timestamp: Market data timestamp
            price: Current price
            symbol_exchange: Exchange name
            security_type: Type of security
            volume: Trading volume
            **kwargs: Additional market data fields
            
        Returns:
            dict: Created or existing market data
        """
        # Check if market data already exists for this symbol and timestamp
        existing = self.session.query(MarketDataModel).filter(
            MarketDataModel.symbol_ticker == symbol_ticker,
            MarketDataModel.timestamp == timestamp,
            MarketDataModel.symbol_exchange == symbol_exchange
        ).first()
        
        if existing:
            return self._to_entity(existing)
        
        try:
            # Create new market data entry
            entity_data = {
                'symbol_ticker': symbol_ticker,
                'symbol_exchange': symbol_exchange,
                'security_type': security_type,
                'timestamp': timestamp,
                'price': price,
                'volume': volume,
                'created_at': datetime.now(),
                **kwargs
            }
            
            # Calculate mid price and spread if bid/ask provided
            if 'bid' in kwargs and 'ask' in kwargs and kwargs['bid'] and kwargs['ask']:
                entity_data['mid_price'] = (float(kwargs['bid']) + float(kwargs['ask'])) / 2
                entity_data['spread'] = float(kwargs['ask']) - float(kwargs['bid'])
            
            # Add to database
            return self.add(entity_data)
            
        except Exception as e:
            print(f"Error creating market data for {symbol_ticker}: {str(e)}")
            return None
    
    def get_or_create(self, symbol_ticker: str, timestamp: Optional[datetime] = None, 
                      price: Optional[float] = None, symbol_exchange: Optional[str] = None,
                      security_type: Optional[str] = None, **kwargs) -> Optional[dict]:
        """
        Get or create market data with dependency resolution.
        
        Args:
            symbol_ticker: Stock ticker symbol (primary identifier)
            timestamp: Market data timestamp (optional, defaults to current datetime)
            price: Current price (optional, defaults to 0)
            symbol_exchange: Exchange name (optional, defaults to "USA")
            security_type: Type of security (optional, defaults to "EQUITY")
            **kwargs: Additional fields for market data (volume, bid, ask, etc.)
            
        Returns:
            Domain market data entity (dict) or None if creation failed
        """
        try:
            # Set defaults
            timestamp = timestamp or datetime.now()
            price = price or 0.0
            symbol_exchange = symbol_exchange or "USA"
            security_type = security_type or "EQUITY"
            
            # Use existing _create_or_get_market_data method
            return self._create_or_get_market_data(
                symbol_ticker=symbol_ticker,
                timestamp=timestamp,
                price=price,
                symbol_exchange=symbol_exchange,
                security_type=security_type,
                **kwargs
            )
            
        except Exception as e:
            print(f"Error in get_or_create for market data ({symbol_ticker}): {e}")
            return None

    # Standard CRUD interface
    def create(self, entity_data: dict) -> dict:
        """Create new market data entity in database (standard CRUD interface)."""
        return self.add(entity_data)