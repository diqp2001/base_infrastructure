"""
FMP Equity Data Repository - handles CRUD operations for FmpEquityData entities.
Follows the standardized repository pattern for managing FMP API data in local database.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from src.infrastructure.models.finance.fmp_equity_data import FmpEquityDataModel
from src.domain.entities.finance.fmp_equity_data import FmpEquityData
from src.infrastructure.repositories.base_repository import BaseRepository


class FmpEquityDataRepository(BaseRepository):
    """Repository for managing FMP Equity Data entities."""
    
    def __init__(self, session: Session):
        super().__init__(session)
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for FmpEquityData."""
        return FmpEquityDataModel
    
    def _to_entity(self, model: FmpEquityDataModel) -> FmpEquityData:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        
        return FmpEquityData(
            id=model.id,
            symbol=model.symbol,
            price=model.price,
            change=model.change,
            changes_percentage=model.changes_percentage,
            day_low=model.day_low,
            day_high=model.day_high,
            year_high=model.year_high,
            year_low=model.year_low,
            market_cap=model.market_cap,
            price_avg_50=model.price_avg_50,
            price_avg_200=model.price_avg_200,
            volume=model.volume,
            avg_volume=model.avg_volume,
            exchange=model.exchange,
            name=model.name,
            pe=model.pe,
            eps=model.eps,
            timestamp=model.timestamp,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    def _to_model(self, entity: FmpEquityData) -> FmpEquityDataModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        
        return FmpEquityDataModel(
            id=entity.id,
            symbol=entity.symbol,
            price=entity.price,
            change=entity.change,
            changes_percentage=entity.changes_percentage,
            day_low=entity.day_low,
            day_high=entity.day_high,
            year_high=entity.year_high,
            year_low=entity.year_low,
            market_cap=entity.market_cap,
            price_avg_50=entity.price_avg_50,
            price_avg_200=entity.price_avg_200,
            volume=entity.volume,
            avg_volume=entity.avg_volume,
            exchange=entity.exchange,
            name=entity.name,
            pe=entity.pe,
            eps=entity.eps,
            timestamp=entity.timestamp,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    def get_all(self) -> List[FmpEquityData]:
        """Retrieve all FMP equity data records."""
        models = self.session.query(FmpEquityDataModel).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_id(self, data_id: int) -> Optional[FmpEquityData]:
        """Retrieve FMP equity data by ID."""
        model = self.session.query(FmpEquityDataModel).filter(
            FmpEquityDataModel.id == data_id
        ).first()
        return self._to_entity(model)
    
    def get_by_symbol(self, symbol: str, limit: Optional[int] = None) -> List[FmpEquityData]:
        """
        Retrieve FMP equity data by symbol, ordered by timestamp descending.
        
        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of records to return (optional)
            
        Returns:
            List of FmpEquityData entities for the symbol
        """
        query = self.session.query(FmpEquityDataModel).filter(
            FmpEquityDataModel.symbol == symbol.upper()
        ).order_by(desc(FmpEquityDataModel.timestamp))
        
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self._to_entity(model) for model in models]
    
    def get_latest_by_symbol(self, symbol: str) -> Optional[FmpEquityData]:
        """Get the most recent data point for a symbol."""
        model = self.session.query(FmpEquityDataModel).filter(
            FmpEquityDataModel.symbol == symbol.upper()
        ).order_by(desc(FmpEquityDataModel.timestamp)).first()
        return self._to_entity(model)
    
    def get_by_symbols(self, symbols: List[str], limit_per_symbol: Optional[int] = 1) -> List[FmpEquityData]:
        """
        Retrieve FMP equity data for multiple symbols.
        
        Args:
            symbols: List of stock ticker symbols
            limit_per_symbol: Maximum records per symbol (1 for latest data)
            
        Returns:
            List of FmpEquityData entities
        """
        results = []
        for symbol in symbols:
            symbol_data = self.get_by_symbol(symbol, limit_per_symbol)
            results.extend(symbol_data)
        return results
    
    def get_by_date_range(self, symbol: str, start_date: datetime, 
                         end_date: datetime) -> List[FmpEquityData]:
        """
        Retrieve FMP equity data for a symbol within a date range.
        
        Args:
            symbol: Stock ticker symbol
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of FmpEquityData entities within the date range
        """
        models = self.session.query(FmpEquityDataModel).filter(
            and_(
                FmpEquityDataModel.symbol == symbol.upper(),
                FmpEquityDataModel.timestamp >= start_date,
                FmpEquityDataModel.timestamp <= end_date
            )
        ).order_by(desc(FmpEquityDataModel.timestamp)).all()
        
        return [self._to_entity(model) for model in models]
    
    def exists_by_symbol_and_timestamp(self, symbol: str, timestamp: datetime) -> bool:
        """Check if data exists for symbol at specific timestamp."""
        return self.session.query(FmpEquityDataModel).filter(
            and_(
                FmpEquityDataModel.symbol == symbol.upper(),
                FmpEquityDataModel.timestamp == timestamp
            )
        ).first() is not None
    
    def add_or_update(self, entity: FmpEquityData) -> FmpEquityData:
        """
        Add new FMP equity data or update existing record.
        Updates based on symbol and timestamp combination.
        
        Args:
            entity: FmpEquityData entity to add or update
            
        Returns:
            The saved/updated entity
        """
        if not entity.symbol:
            raise ValueError("Symbol is required for FMP equity data")
        
        if not entity.timestamp:
            entity.timestamp = datetime.utcnow()
        
        # Check if record already exists for this symbol and timestamp
        existing_model = self.session.query(FmpEquityDataModel).filter(
            and_(
                FmpEquityDataModel.symbol == entity.symbol.upper(),
                FmpEquityDataModel.timestamp == entity.timestamp
            )
        ).first()
        
        if existing_model:
            # Update existing record
            for attr in ['price', 'change', 'changes_percentage', 'day_low', 'day_high',
                        'year_high', 'year_low', 'market_cap', 'price_avg_50', 'price_avg_200',
                        'volume', 'avg_volume', 'exchange', 'name', 'pe', 'eps']:
                value = getattr(entity, attr)
                if value is not None:
                    setattr(existing_model, attr, value)
            
            existing_model.updated_at = datetime.utcnow()
            self.session.commit()
            return self._to_entity(existing_model)
        else:
            # Add new record
            if not entity.created_at:
                entity.created_at = datetime.utcnow()
            
            model = self._to_model(entity)
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)
            return self._to_entity(model)
    
    def bulk_add_or_update(self, entities: List[FmpEquityData]) -> List[FmpEquityData]:
        """
        Bulk add or update multiple FMP equity data records.
        More efficient for large datasets.
        
        Args:
            entities: List of FmpEquityData entities
            
        Returns:
            List of saved entities
        """
        saved_entities = []
        for entity in entities:
            saved_entity = self.add_or_update(entity)
            saved_entities.append(saved_entity)
        return saved_entities
    
    def delete_old_data(self, symbol: str, days_to_keep: int = 365) -> int:
        """
        Delete old data for a symbol, keeping only recent records.
        
        Args:
            symbol: Stock ticker symbol
            days_to_keep: Number of days of data to retain
            
        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        deleted_count = self.session.query(FmpEquityDataModel).filter(
            and_(
                FmpEquityDataModel.symbol == symbol.upper(),
                FmpEquityDataModel.timestamp < cutoff_date
            )
        ).delete()
        
        self.session.commit()
        return deleted_count
    
    def get_symbols_list(self) -> List[str]:
        """Get list of unique symbols in the database."""
        result = self.session.query(FmpEquityDataModel.symbol).distinct().all()
        return [row[0] for row in result]
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary statistics about stored FMP equity data."""
        total_records = self.session.query(FmpEquityDataModel).count()
        unique_symbols = len(self.get_symbols_list())
        
        # Get date range
        oldest_record = self.session.query(FmpEquityDataModel.timestamp).order_by(
            FmpEquityDataModel.timestamp.asc()
        ).first()
        newest_record = self.session.query(FmpEquityDataModel.timestamp).order_by(
            FmpEquityDataModel.timestamp.desc()
        ).first()
        
        return {
            'total_records': total_records,
            'unique_symbols': unique_symbols,
            'oldest_data': oldest_record[0] if oldest_record else None,
            'newest_data': newest_record[0] if newest_record else None
        }
    
    # Standard CRUD interface
    def create(self, entity: FmpEquityData) -> FmpEquityData:
        """Create new FMP equity data entity in database (standard CRUD interface)."""
        return self.add_or_update(entity)