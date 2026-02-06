"""
Financial Asset Service - handles creation and management of financial asset entities.
Provides a service layer for creating financial asset domain entities like Company, CompanyShare, Currency, etc.
"""

from typing import List, Optional, Any, Type
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.orm import Session
from src.dto.factor.factor_batch import FactorBatch
from src.dto.factor.factor_value_batch import FactorValueBatch






# Import MarketData for entity information


from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository
from src.application.services.database_service.database_service import DatabaseService

from src.domain.entities.finance.financial_assets.index.index import Index

from src.infrastructure.repositories.local_repo.factor.factor_repository import FactorRepository
from src.infrastructure.repositories.local_repo.factor.factor_value_repository import FactorValueRepository
from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_repository import IBKRFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.bond_repository import IBKRBondRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.cash_repository import IBKRCashRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.commodity_repository import IBKRCommodityRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.company_share_repository import IBKRCompanyShareRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.crypto_repository import IBKRCryptoRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.currency_repository import IBKRCurrencyRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.equity_repository import IBKREquityRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.etf_share_repository import IBKRETFShareRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.derivatives.future.index_future_repository import IBKRIndexFutureRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.index_repository import IBKRIndexRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.security_repository import IBKRSecurityRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.share_repository import IBKRShareRepository
from src.infrastructure.repositories.repository_factory import RepositoryFactory
from src.infrastructure.repositories.local_repo.finance.financial_assets.bond_repository import BondRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.cash_repository import CashRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.commodity_repository import CommodityRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.crypto_repository import CryptoRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.currency_repository import CurrencyRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.equity_repository import EquityRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.etf_share_repository import ETFShareRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.future.index_future_repository import IndexFutureRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.index_repository import IndexRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.security_repository import SecurityRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.share_repository import ShareRepository





class EntityService:
    """Service for creating and managing financial asset domain entities."""

    def __init__(self, database_service: Optional[DatabaseService] = None, db_type: str = 'sqlite', ibkr_client=None):
        """
        Initialize the service with a database service or create one if not provided.

        Args:
            database_service: Optional existing DatabaseService instance
            db_type: Database type to use when creating new DatabaseService (ignored if database_service provided)
            ibkr_client: Optional IBKR client for creating IBKR repositories
        """
        if database_service is not None:
            self.database_service = database_service
        else:
            self.database_service = DatabaseService(db_type)

        self.session = self.database_service.session
        
        # Create factory with optional IBKR client
        self.repository_factory = RepositoryFactory(self.session, ibkr_client)
        
        
        

    
    def create_local_repositories(self) -> dict:
        """
        Legacy method for backward compatibility.
        Now delegates to repository factory.

        Returns:
            Dictionary with local repository implementations
        """
        return self.repository_factory.create_local_repositories()
    def create_ibkr_client(self):
        """
        Legacy method for backward compatibility.
        Now delegates to repository factory.
        """
        return self.repository_factory.create_ibkr_client()

    def create_ibkr_repositories(self, ibkr_client=None) -> Optional[dict]:
        """
        Legacy method for backward compatibility.
        Now delegates to repository factory.

        Args:
            ibkr_client: Optional Interactive Brokers API client

        Returns:
            Dictionary with IBKR repository implementations or None if no client
        """
        return self.repository_factory.create_ibkr_repositories(ibkr_client)

    
    def get_local_repository(self, entity_class: type):
        """
        Return the repository associated with a given domain entity class.
        Now delegates to repository factory.

        Args:
            entity_class: Domain entity class (e.g. FactorValue)

        Returns:
            Repository instance managing that entity
        """
        repo = self.repository_factory.get_local_repository(entity_class)
        if not repo:
            raise ValueError(
                f"No repository registered for entity class: {entity_class.__name__}"
            )
        return repo


    

    def get_ibkr_repository(self, entity_class: type):
        """
        Return the repository associated with a given domain entity class.
        Now delegates to repository factory.

        Args:
            entity_class: Domain entity class (e.g. FactorValue)

        Returns:
            Repository instance managing that entity or None if no IBKR client
        """
        return self.repository_factory.get_ibkr_repository(entity_class)
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

    def _create_or_get(self, entity_cls ,name: str,
                            **kwargs) :
        try:
            repository = self.get_local_repository(entity_cls)
            return repository._create_or_get(entity_cls,name,
                            **kwargs)


        except Exception as e:
            self.logger.error(
                f"Error pulling {entity_cls.__name__} with symbol {name}: {e}"
            )

    def _create_or_get_ibkr(self, entity_cls: object, entity_symbol: str = None, entity_id: int = None,
                            **kwargs) -> Optional[object]:
        """
        Create index entity if it doesn't exist, otherwise return existing.
        Follows the same pattern as CompanyShareRepository._create_or_get_company_share().

        Args:
            entity_cls: Entity class to create/get
            entity_symbol: Symbol (unique identifier)
            entity_id: Optional entity ID
            **kwargs: Additional parameters

        Returns:
            Entity: Created or existing entity or None if no IBKR client
        """
        try:
            # Check if entity already exists by symbol
            ibkr_repository = self.get_ibkr_repository(entity_cls)
            
            if not ibkr_repository:
                print(f"No IBKR repository available for {entity_cls.__name__}")
                return None

            # Get entity information from IBKR API
            entity = ibkr_repository._create_or_get(entity_symbol,**kwargs)

            return entity

        except Exception as e:
            print(f"Error creating/getting {entity_cls.__name__} for symbol {entity_symbol}: {str(e)}")
            return None

    def get_or_create_batch_local(
        self, 
        entity_class: Type, 
        batch_data: List[Dict[str, Any]], 
        batch_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Generic batch get_or_create service for any entity type using local repositories.
        
        This method provides a unified interface for batch operations across all entity types,
        not just factors and factor values.
        
        Args:
            entity_class: The domain entity class (e.g., Factor, FactorValue, CompanyShare)
            batch_data: List of dictionaries containing entity creation parameters
            batch_metadata: Optional metadata for the batch operation
            
        Returns:
            List of created/retrieved entity instances
        """
        try:
            if not batch_data:
                print("Cannot process empty batch data")
                return []
            
            repository = self.get_local_repository(entity_class)
            if not repository:
                print(f"No local repository found for {entity_class.__name__}")
                return []
            
            results = []
            
            # Check if repository has native batch support
            if hasattr(repository, 'get_or_create_batch'):
                results = repository.get_or_create_batch(batch_data, batch_metadata)
            else:
                # Fallback to individual get_or_create operations
                for item_data in batch_data:
                    try:
                        if hasattr(repository, '_create_or_get'):
                            entity = repository._create_or_get(**item_data)
                        elif hasattr(repository, 'get_or_create'):
                            entity = repository.get_or_create(**item_data)
                        else:
                            print(f"Repository {repository.__class__.__name__} doesn't support get_or_create operations")
                            continue
                        
                        if entity:
                            results.append(entity)
                            
                    except Exception as item_error:
                        print(f"Error processing batch item: {item_error}")
                        continue
            
            print(f"Batch processed: {len(results)}/{len(batch_data)} entities created/retrieved")
            return results
            
        except Exception as e:
            print(f"Error in generic batch get_or_create: {e}")
            return []

    def get_or_create_batch_ibkr(
        self, 
        entity_class: Type, 
        batch_data: List[Dict[str, Any]], 
        batch_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Generic batch get_or_create service for any entity type using IBKR repositories.
        
        Args:
            entity_class: The domain entity class
            batch_data: List of dictionaries containing entity creation parameters
            batch_metadata: Optional metadata for the batch operation
            
        Returns:
            List of created/retrieved entity instances
        """
        try:
            if not batch_data:
                print("Cannot process empty batch data")
                return []
            
            repository = self.get_ibkr_repository(entity_class)
            if not repository:
                print(f"No IBKR repository found for {entity_class.__name__}")
                return []
            
            results = []
            
            # Check if repository has native batch support
            if hasattr(repository, 'get_or_create_batch'):
                results = repository.get_or_create_batch(batch_data, batch_metadata)
            else:
                # Fallback to individual get_or_create operations
                for item_data in batch_data:
                    try:
                        if hasattr(repository, '_create_or_get_ibkr'):
                            entity = repository._create_or_get_ibkr(**item_data)
                        elif hasattr(repository, '_create_or_get'):
                            entity = repository._create_or_get(**item_data)
                        elif hasattr(repository, 'get_or_create'):
                            entity = repository.get_or_create(**item_data)
                        else:
                            print(f"IBKR Repository {repository.__class__.__name__} doesn't support get_or_create operations")
                            continue
                        
                        if entity:
                            results.append(entity)
                            
                    except Exception as item_error:
                        print(f"Error processing IBKR batch item: {item_error}")
                        continue
            
            print(f"IBKR Batch processed: {len(results)}/{len(batch_data)} entities created/retrieved")
            return results
            
        except Exception as e:
            print(f"Error in generic IBKR batch get_or_create: {e}")
            return []

    def get_or_create_factor_value_batch(
        self, 
        factor_batch: FactorBatch,
        entity_id: int,
        time_date: str,
        financial_asset_entity: Optional[Any] = None,
        use_ibkr: bool = True
    ) -> Optional[FactorValueBatch]:
        """
        Specialized batch method for FactorValue creation.
        
        Args:
            factor_batch: FactorBatch DTO containing factors
            entity_id: ID of the financial asset entity
            time_date: Date string in 'YYYY-MM-DD HH:MM:SS' format
            financial_asset_entity: Optional financial asset entity object
            use_ibkr: Whether to use IBKR repository (True) or local repository (False)
            
        Returns:
            FactorValueBatch DTO or None if failed
        """
        try:
            from src.domain.entities.factor.factor_value import FactorValue
            
            # Add metadata to factor batch
            factor_batch.metadata = factor_batch.metadata or {}
            factor_batch.metadata.update({
                'entity_id': entity_id,
                'time_date': time_date,
                'financial_asset_entity': financial_asset_entity
            })
            
            if use_ibkr:
                # Use IBKR repository
                ibkr_repo = self.get_ibkr_repository(FactorValue)
                if ibkr_repo and hasattr(ibkr_repo, 'get_or_create_batch'):
                    return ibkr_repo.get_or_create_batch(factor_batch)
                else:
                    print("IBKR FactorValue repository doesn't support batch operations")
                    return None
            else:
                # Use local repository
                local_repo = self.get_local_repository(FactorValue)
                if local_repo and hasattr(local_repo, 'get_or_create_batch'):
                    return local_repo.get_or_create_batch(factor_batch)
                else:
                    print("Local FactorValue repository doesn't support batch operations")
                    return None
                    
        except Exception as e:
            print(f"Error in factor value batch creation: {e}")
            return None