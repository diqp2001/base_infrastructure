"""
Financial Asset Service - handles creation and management of financial asset entities.
Provides a service layer for creating financial asset domain entities like Company, CompanyShare, Currency, etc.
"""

from typing import Optional, List, Dict, Any, Type
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


from infrastructure.repositories.local_repo.finance.financial_assets.index_repository import IndexRepository
from src.domain.entities.finance.company import Company
from src.domain.entities.finance.exchange import Exchange
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.financial_assets.currency import Currency
from src.domain.entities.finance.financial_assets.crypto import Crypto
from src.domain.entities.finance.financial_assets.commodity import Commodity
from src.domain.entities.finance.financial_assets.cash import Cash
from src.domain.entities.finance.financial_assets.bond import Bond
from domain.entities.finance.financial_assets.index.index import Index
from src.domain.entities.finance.financial_assets.share.etf_share import ETFShare
from src.domain.entities.finance.financial_assets.security import Security
from src.domain.entities.finance.financial_assets.share.share import Share
from src.domain.entities.finance.financial_assets.derivatives.future.future import Future
from src.domain.entities.finance.financial_assets.derivatives.option.option import Option
from src.domain.entities.finance.financial_assets.stock import Stock
from src.domain.entities.finance.financial_assets.equity import Equity
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset
from src.domain.entities.finance.financial_assets.derivatives.forward import Forward

# Import existing repositories
from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.currency_repository import CurrencyRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.bond_repository import BondRepository
from src.application.services.database_service.database_service import DatabaseService

# Import infrastructure models for Index and Future
from src.infrastructure.models.finance.financial_assets.index import Index as IndexModel
from infrastructure.models.finance.financial_assets.future import Future as FutureModel

# Import MarketData for entity information


class FinancialAssetService:
    """Service for creating and managing financial asset domain entities."""
    
    def __init__(self, database_service: Optional[DatabaseService] = None, db_type: str = 'sqlite'):
        """
        Initialize the service with a database service or create one if not provided.
        
        Args:
            database_service: Optional existing DatabaseService instance
            db_type: Database type to use when creating new DatabaseService (ignored if database_service provided)
        """
        if database_service is not None:
            self.database_service = database_service
        else:
            self.database_service = DatabaseService(db_type)
        
        self.session = self.database_service.session
        self._repositories = {
        CompanyShare: CompanyShareRepository,
        Currency: CurrencyRepository,
        Bond: BondRepository,
        Index: IndexRepository,
        }
        
    def get_repository(self, entity_type):
        """
        Return the repository associated with a domain entity type.
        """
        repo = self._repositories.get(entity_type)
        if repo is None:
            raise ValueError(f"No repository registered for entity type: {entity_type.__name__}")
        repo = repo(self.session)
        return repo
    
    
    
    
    
    
        
   
        
    def persist_entity(self, entity) :
        """
        Persist a bond entity to the database.
        
        Args:
            bond: Bond entity to persist
            
        Returns:
            Persisted bond entity or None if failed
        """
        try:
            entity_cls = type(entity)
            repository = self.get_repository(entity_cls)
            if repository:
                return repository.add(entity)
            else:
                print("repository not available")
                return None
        except Exception as e:
            print(f"Error persisting entity {entity.symbol if hasattr(entity, 'symbol') else 'unknown'}: {str(e)}")
            return None
    
        
    def pull_by_id(self, entity_cls, entity_id: int):
        """
        Generic pull method for any entity by ID.
        """
        try:
            repository = self.get_repository(entity_cls)
            return repository.get_by_id(entity_id)
        except Exception as e:
            self.logger.error(
                f"Error pulling {entity_cls.__name__} with ID {entity_id}: {e}"
            )
            return None
        
    def pull_all(self,entity_cls) -> List:
        """Pull all company shares from database."""
        try:
            repository = self.get_repository(entity_cls)
            return repository.get_all()
        except Exception as e:
            print(f"Error pulling all : {str(e)}")
            return []
    
    
    
    # Enhanced methods following company_share_repository patterns
    def get_by_symbol(self, entity_cls ,symbol: str) -> Optional[Index]:
        """
        Get index by symbol from database, following get_by_ticker pattern.
        
        Args:
            symbol: Index symbol (e.g., 'SPX', 'NASDAQ')
            
        Returns:
            Index entity or None if not found
        """
        try:
            repository = self.get_repository(entity_cls)
            return repository.get_by_symbol(symbol)
        
            
        except Exception as e:
            self.logger.error(
                f"Error pulling {entity_cls.__name__} with symbol {symbol}: {e}"
            )
    
    def _create_ibkr_or_get(self, entity_cls, entity_id: int,
                            **kwargs) -> Optional[Index]:
        """
        Create index entity if it doesn't exist, otherwise return existing.
        Follows the same pattern as CompanyShareRepository._create_or_get_company_share().
        
        Args:
            symbol: Index symbol (unique identifier)
            exchange: Exchange where index is listed
            currency: Index currency
            name: Index name for entity setup
            **kwargs: Additional index parameters
            
        Returns:
            Index entity: Created or existing entity
        """
        try:
            entity_cls.id
            # Check if entity already exists by symbol
            repository = self.get_repository(entity_cls)
            existing_entity = self.pull_by_id(entity_cls,entity_cls.id)
            if existing_entity:
                return existing_entity
            
            # Get index information from MarketData if available
            info, entity = repository._get_info_from_market_data_ibkr(entity_cls.symbol, entity_cls.exchange, entity_cls.currency)
            
            return entity
            
        except Exception as e:
            print(f"Error creating/getting index for {entity_cls.symbol}: {str(e)}")
            return None

    def _ensure_index_exists(self, symbol: str, exchange: str = "CBOE", currency: str = "USD", name: str = None, **kwargs) -> Optional[Index]:
        """
        Ensure Index entity exists, create if it doesn't exist.
        Follows the same pattern as CompanyShareRepository._create_or_get_company_share().
        
        Args:
            symbol: Index symbol (e.g., 'SPX')
            exchange: Exchange where index is listed  
            currency: Index currency
            name: Index name for entity setup
            **kwargs: Additional index parameters
            
        Returns:
            Index entity: Created or existing entity
        """
        try:
            # Check if index already exists by symbol
            existing_index = self.get_by_symbol(Index, symbol)
            if existing_index:
                return existing_index
            
            # Create new index entity using domain entity
            index_entity = Index(
                symbol=symbol,
                name=name or f"{symbol} Index",
                exchange=exchange,
                currency=currency,
                **kwargs
            )
            
            # Persist the index entity
            persisted_index = self.persist_entity(index_entity)
            
            if persisted_index:
                print(f"✅ Created Index entity for {symbol}")
                return persisted_index
            else:
                print(f"❌ Failed to persist Index entity for {symbol}")
                return None
                
        except Exception as e:
            print(f"Error ensuring Index exists for {symbol}: {str(e)}")
            return None

    def _ensure_index_future_exists(self, symbol: str, underlying_symbol: str, exchange: str = "CME", 
                                    currency: str = "USD", expiry_date=None, contract_size: str = "$50", **kwargs) -> Optional[Future]:
        """
        Ensure Index Future entity exists, create if it doesn't exist.
        Follows the same pattern as CompanyShareRepository._create_or_get_company_share().
        
        Args:
            symbol: Future symbol (e.g., 'ES')
            underlying_symbol: Underlying index symbol (e.g., 'SPX')
            exchange: Exchange where future is listed
            currency: Future currency
            expiry_date: Future expiry date
            contract_size: Contract size specification
            **kwargs: Additional future parameters
            
        Returns:
            Future entity: Created or existing entity
        """
        try:
            from datetime import date
            
            # Check if future already exists by symbol
            existing_future = self.get_by_symbol(Future, symbol)
            if existing_future:
                return existing_future
            
            # Default expiry date if not provided
            if not expiry_date:
                expiry_date = date(2025, 12, 31)
            
            # Create new future entity using domain entity
            future_entity = Future(
                symbol=symbol,
                underlying_asset=underlying_symbol,
                expiry_date=expiry_date,
                contract_size=contract_size,
                exchange=exchange,
                currency=currency,
                **kwargs
            )
            
            # Persist the future entity
            persisted_future = self.persist_entity(future_entity)
            
            if persisted_future:
                print(f"✅ Created Future entity for {symbol} (underlying: {underlying_symbol})")
                return persisted_future
            else:
                print(f"❌ Failed to persist Future entity for {symbol}")
                return None
                
        except Exception as e:
            print(f"Error ensuring Future exists for {symbol}: {str(e)}")
            return None
    
    