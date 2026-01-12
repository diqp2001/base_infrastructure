"""
Financial Asset Service - handles creation and management of financial asset entities.
Provides a service layer for creating financial asset domain entities like Company, CompanyShare, Currency, etc.
"""

from typing import Optional, List, Dict, Any, Type
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.orm import Session


from application.services.misbuffet.brokers.broker_factory import create_interactive_brokers_broker
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.index_future_repository import IBKRIndexFutureRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.index_future_repository import IndexFutureRepository
from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture
from src.domain.entities.finance.company import Company
from src.domain.entities.finance.exchange import Exchange
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.financial_assets.currency import Currency
from src.domain.entities.finance.financial_assets.crypto import Crypto
from src.domain.entities.finance.financial_assets.commodity import Commodity
from src.domain.entities.finance.financial_assets.cash import Cash
from src.domain.entities.finance.financial_assets.bond import Bond
from src.domain.entities.finance.financial_assets.index.index import Index
from src.domain.entities.finance.financial_assets.share.etf_share import ETFShare
from src.domain.entities.finance.financial_assets.security import Security
from src.domain.entities.finance.financial_assets.share.share import Share
from src.domain.entities.finance.financial_assets.derivatives.future.future import Future
from src.domain.entities.finance.financial_assets.derivatives.option.option import Option
from src.domain.entities.finance.financial_assets.stock import Stock
from src.domain.entities.finance.financial_assets.equity import Equity
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset
from src.domain.entities.finance.financial_assets.derivatives.forward import Forward

# Import existing local repositories
from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.currency_repository import CurrencyRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.bond_repository import BondRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.index_repository import IndexRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.crypto_repository import CryptoRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.commodity_repository import CommodityRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.cash_repository import CashRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.equity_repository import EquityRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.etf_share_repository import ETFShareRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.share_repository import ShareRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.security_repository import SecurityRepository

# Import IBKR repositories
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.company_share_repository import IBKRCompanyShareRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.currency_repository import IBKRCurrencyRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.bond_repository import IBKRBondRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.index_repository import IBKRIndexRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.crypto_repository import IBKRCryptoRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.commodity_repository import IBKRCommodityRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.cash_repository import IBKRCashRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.equity_repository import IBKREquityRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.etf_share_repository import IBKREtfShareRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.share_repository import IBKRShareRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.security_repository import IBKRSecurityRepository
from src.application.services.database_service.database_service import DatabaseService

# Import infrastructure models for Index and Future
from src.infrastructure.models.finance.financial_assets.index import Index as IndexModel
from src.infrastructure.models.finance.financial_assets.future import Future as FutureModel

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
    
    
    def create_local_repositories(self) -> dict:
        """
        Create local-only repository configuration.
        
        Args:
            session: SQLAlchemy session for database operations
            
        Returns:
            Dictionary with repository implementations
        """
        self.local_repositories = {
            'index_future': IndexFutureRepository(self.session),
            'company_share': CompanyShareRepository(self.session),
            'currency': CurrencyRepository(self.session),
            'bond': BondRepository(self.session),
            'index': IndexRepository(self.session),
            'crypto': CryptoRepository(self.session),
            'commodity': CommodityRepository(),  # No session parameter
            'cash': CashRepository(self.session),
            'equity': EquityRepository(self.session),
            'etf_share': ETFShareRepository(),  # No session parameter
            'share': ShareRepository(self.session),
            'security': SecurityRepository()  # No session parameter
        }
        return self.local_repositories
    def create_ibkr_client(self):
        self.ib_config = {
            'host': "127.0.0.1",
            'port': 7497,
            'client_id': 1,
            'timeout': 60,
            'account_id': 'DEFAULT',
            'enable_logging': True
        }
        self.ib_broker = create_interactive_brokers_broker(**self.ib_config)
        self.ib_broker.connect()
    
    def create_ibkr_repositories(self,
        
        ibkr_client=None
    ) -> dict:
        """
        Create IBKR-backed repository configuration.
        
        Args:
            session: SQLAlchemy session for local persistence
            ibkr_client: Interactive Brokers API client
            
        Returns:
            Dictionary with repository implementations
        """
        # Create local repositories first
        self.create_local_repositories()
        self.create_ibkr_client()
        
        # Wrap local repositories with IBKR implementations
        self.ibkr_repositories = {
            'index_future': IBKRIndexFutureRepository(
                ibkr_client=self.ib_broker,
                local_repo=self.local_repositories['index_future']
            ),
            'company_share': IBKRCompanyShareRepository(
                ibkr_client=self.ib_broker,
                local_repo=self.local_repositories['company_share']
            ),
            'currency': IBKRCurrencyRepository(
                ibkr_client=self.ib_broker,
                local_repo=self.local_repositories['currency']
            ),
            'bond': IBKRBondRepository(
                ibkr_client=self.ib_broker,
                local_repo=self.local_repositories['bond']
            ),
            'index': IBKRIndexRepository(
                ibkr_client=self.ib_broker,
                local_repo=self.local_repositories['index']
            ),
            'crypto': IBKRCryptoRepository(
                ibkr_client=self.ib_broker,
                local_repo=self.local_repositories['crypto']
            ),
            'commodity': IBKRCommodityRepository(
                ibkr_client=self.ib_broker,
                local_repo=self.local_repositories['commodity']
            ),
            'cash': IBKRCashRepository(
                ibkr_client=self.ib_broker,
                local_repo=self.local_repositories['cash']
            ),
            'equity': IBKREquityRepository(
                ibkr_client=self.ib_broker,
                local_repo=self.local_repositories['equity']
            ),
            'etf_share': IBKREtfShareRepository(
                ibkr_client=self.ib_broker,
                local_repo=self.local_repositories['etf_share']
            ),
            'share': IBKRShareRepository(
                ibkr_client=self.ib_broker,
                local_repo=self.local_repositories['share']
            ),
            'security': IBKRSecurityRepository(
                ibkr_client=self.ib_broker,
                local_repo=self.local_repositories['security']
            )
        }
        return self.ibkr_repositories
        
    def get_local_repository(self, entity_type):
        """
        Return the repository associated with a domain entity type.
        """
        repo = self.local_repositories.get(entity_type)
        if repo is None:
            raise ValueError(f"No repository registered for entity type: {entity_type.__name__}")
        repo = repo(self.session)
        return repo
    
    def get_ibkr_repository(self, entity_type):
        """
        Return the repository associated with a domain entity type.
        """
        repo = self.ibkr_repositories.get(entity_type)
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
            repository = self.get_local_repository(entity_cls)
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
            repository = self.get_local_repository(entity_cls)
            return repository.get_by_id(entity_id)
        except Exception as e:
            self.logger.error(
                f"Error pulling {entity_cls.__name__} with ID {entity_id}: {e}"
            )
            return None
        

    def pull_all(self,entity_cls) -> List:
        """Pull all company shares from database."""
        try:
            repository = self.get_local_repository(entity_cls)
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
            repository = self.get_local_repository(entity_cls)
            return repository.get_by_symbol(symbol)
        
            
        except Exception as e:
            self.logger.error(
                f"Error pulling {entity_cls.__name__} with symbol {symbol}: {e}"
            )

    def _create_or_get(self, entity_cls ,name: str) :
        try:
            repository = self.get_local_repository(entity_cls)
            return repository._create_or_get(entity_cls,name)
        
            
        except Exception as e:
            self.logger.error(
                f"Error pulling {entity_cls.__name__} with symbol {name}: {e}"
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
            ibkr_repository = self.get_ibkr_repository(entity_cls)
            
            
            # Get index information from MarketData if available
            entity = ibkr_repository.get_or_create(entity_cls.symbol)
            
            return entity
            
        except Exception as e:
            print(f"Error creating/getting index for {entity_cls.symbol}: {str(e)}")
            return None
    
    