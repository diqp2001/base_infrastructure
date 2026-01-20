"""
Repository Factory - Centralized creation and dependency injection for repositories.

This factory manages the creation of local and IBKR repositories with proper dependency injection,
following the Domain-Driven Design principles and eliminating direct parameter passing.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

# Local repositories
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository
from src.infrastructure.repositories.local_repo.factor.factor_repository import FactorRepository
from src.infrastructure.repositories.local_repo.factor.factor_value_repository import FactorValueRepository
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

# IBKR repositories
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


class RepositoryFactory:
    """
    Factory for creating and managing repository instances with proper dependency injection.
    
    This factory centralizes repository creation and manages dependencies between repositories,
    providing clean separation of concerns and making IBKR client optional.
    """

    def __init__(self, session: Session, ibkr_client=None):
        """
        Initialize repository factory.
        
        Args:
            session: SQLAlchemy session for database operations
            ibkr_client: Optional Interactive Brokers API client
        """
        self.session = session
        self.ibkr_client = ibkr_client
        self._local_repositories = {}
        self._ibkr_repositories = {}

    def create_local_repositories(self) -> Dict[str, Any]:
        """
        Create and cache local repository instances.
        
        Returns:
            Dictionary mapping repository names to instances
        """
        if not self._local_repositories:
            self._local_repositories = {
                'factor_value': FactorValueRepository(self.session),
                'factor': FactorRepository(self.session),
                'base_factor': BaseFactorRepository(self.session),
                'share_factor': ShareFactorRepository(self.session),
                'index_future': IndexFutureRepository(self.session),
                'company_share': CompanyShareRepository(self.session, factory=self),
                'currency': CurrencyRepository(self.session),
                'bond': BondRepository(self.session),
                'index': IndexRepository(self.session),
                'crypto': CryptoRepository(self.session),
                'commodity': CommodityRepository(self.session),  
                'cash': CashRepository(self.session),
                'equity': EquityRepository(self.session),
                'etf_share': ETFShareRepository(self.session),  
                'share': ShareRepository(self.session),
                'security': SecurityRepository(self.session)
            }
        return self._local_repositories

    def create_ibkr_repositories(self, ibkr_client=None) -> Optional[Dict[str, Any]]:
        """
        Create and cache IBKR repository instances if IBKR client is available.
        
        Args:
            ibkr_client: Optional IBKR client override
            
        Returns:
            Dictionary mapping repository names to IBKR instances, or None if no client
        """
        # Use provided client or factory default
        client = ibkr_client or self.ibkr_client
        
        if not client:
            print("No IBKR client available - IBKR repositories cannot be created")
            return None

        if not self._ibkr_repositories:
            # Ensure local repositories exist first
            local_repos = self.create_local_repositories()
            
            self._ibkr_repositories = {
                'factor': IBKRFactorRepository(
                    ibkr_client=client,
                    local_repo=local_repos['factor'],
                    factory=self
                ),
                'factor_value': IBKRFactorValueRepository(
                    ibkr_client=client,
                    local_repo=local_repos['factor_value']
                ),
                'index_future': IBKRIndexFutureRepository(
                    ibkr_client=client,
                    local_repo=local_repos['index_future']
                ),
                'company_share': IBKRCompanyShareRepository(
                    ibkr_client=client,
                    local_repo=local_repos['company_share'],
                    factory=self
                ),
                'currency': IBKRCurrencyRepository(
                    ibkr_client=client,
                    local_repo=local_repos['currency'],
                    factory=self
                ),
                'bond': IBKRBondRepository(
                    ibkr_client=client,
                    local_repo=local_repos['bond'],
                    factory=self
                ),
                'index': IBKRIndexRepository(
                    ibkr_client=client,
                    local_repo=local_repos['index'],
                    factory=self  # Pass factory for dependency injection
                ),
                'crypto': IBKRCryptoRepository(
                    ibkr_client=client,
                    local_repo=local_repos['crypto']
                ),
                'commodity': IBKRCommodityRepository(
                    ibkr_client=client,
                    local_repo=local_repos['commodity'],
                    factory=self
                ),
                'cash': IBKRCashRepository(
                    ibkr_client=client,
                    local_repo=local_repos['cash'],
                    factory=self
                ),
                'equity': IBKREquityRepository(
                    ibkr_client=client,
                    local_repo=local_repos['equity'],
                    factory=self
                ),
                'etf_share': IBKRETFShareRepository(
                    ibkr_client=client,
                    local_repo=local_repos['etf_share'],
                    factory=self
                ),
                'share': IBKRShareRepository(
                    ibkr_client=client,
                    local_repo=local_repos['share'],
                    factory=self
                ),
                'security': IBKRSecurityRepository(
                    ibkr_client=client,
                    local_repo=local_repos['security'],
                    factory=self
                )
            }
        return self._ibkr_repositories

    def create_ibkr_client(self) -> Optional[Any]:
        """
        Create IBKR client using broker factory if not already provided.
        
        Returns:
            IBKR client instance or None if creation failed
        """
        if self.ibkr_client:
            return self.ibkr_client
            
        try:
            from src.application.services.misbuffet.brokers.broker_factory import create_interactive_brokers_broker
            
            ib_config = {
                'host': "127.0.0.1",
                'port': 7497,
                'client_id': 1,
                'timeout': 60,
                'account_id': 'DEFAULT',
                'enable_logging': True
            }
            
            client = create_interactive_brokers_broker(**ib_config)
            client.connect()
            
            self.ibkr_client = client
            return client
            
        except Exception as e:
            print(f"Error creating IBKR client: {e}")
            return None

    @property
    def currency_repo(self):
        """Get currency repository for dependency injection."""
        local_repos = self.create_local_repositories()
        return local_repos.get('currency')

    def get_local_repository(self, entity_class: type):
        """
        Get local repository for a given entity class.
        
        Args:
            entity_class: Domain entity class
            
        Returns:
            Repository instance or None if not found
        """
        repos = self.create_local_repositories()
        for repo in repos.values():
            if hasattr(repo, 'entity_class') and repo.entity_class is entity_class:
                return repo
        return None

    def get_ibkr_repository(self, entity_class: type):
        """
        Get IBKR repository for a given entity class.
        
        Args:
            entity_class: Domain entity class
            
        Returns:
            Repository instance or None if not found or no IBKR client
        """
        repos = self.create_ibkr_repositories()
        if not repos:
            return None
            
        for repo in repos.values():
            if hasattr(repo, 'entity_class') and repo.entity_class is entity_class:
                return repo
        return None

    def has_ibkr_client(self) -> bool:
        """Check if IBKR client is available."""
        return self.ibkr_client is not None