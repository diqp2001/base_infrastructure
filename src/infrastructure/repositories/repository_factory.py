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

# Local Factor repositories
from src.infrastructure.repositories.local_repo.factor.continent_factor_repository import ContinentFactorRepository
from src.infrastructure.repositories.local_repo.factor.country_factor_repository import CountryFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.index_factor_repository import IndexFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.currency_factor_repository import CurrencyFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.equity_factor_repository import EquityFactorRepository
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
from src.infrastructure.repositories.local_repo.geographic.country_repository import CountryRepository
from src.infrastructure.repositories.local_repo.geographic.continent_repository import ContinentRepository
from src.infrastructure.repositories.local_repo.finance.exchange_repository import ExchangeRepository

# IBKR repositories
from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_repository import IBKRFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository

# IBKR Factor repositories
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_continent_factor_repository import IBKRContinentFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_country_factor_repository import IBKRCountryFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_index_factor_repository import IBKRIndexFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_share_factor_repository import IBKRShareFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_currency_factor_repository import IBKRCurrencyFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_equity_factor_repository import IBKREquityFactorRepository
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
from src.infrastructure.repositories.ibkr_repo.finance.country_repository import IBKRCountryRepository
from src.infrastructure.repositories.ibkr_repo.finance.continent_repository import IBKRContinentRepository
from src.infrastructure.repositories.ibkr_repo.finance.exchange_repository import IBKRExchangeRepository


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
        self.create_local_repositories()
        if ibkr_client:
            self.create_ibkr_repositories()

    def create_local_repositories(self) -> Dict[str, Any]:
        """
        Create and cache local repository instances.
        
        Returns:
            Dictionary mapping repository names to instances
        """
        if not self._local_repositories:
            self._local_repositories = {
                'factor_value': FactorValueRepository(self.session, factory=self),
                'factor': FactorRepository(self.session, factory=self),
                # Individual factor repositories
                'continent_factor': ContinentFactorRepository(self.session, factory=self),
                'country_factor': CountryFactorRepository(self.session, factory=self),
                'index_factor': IndexFactorRepository(self.session, factory=self),
                'share_factor': ShareFactorRepository(self.session, factory=self),
                'currency_factor': CurrencyFactorRepository(self.session, factory=self),
                'equity_factor': EquityFactorRepository(self.session, factory=self),
                'index_future': IndexFutureRepository(self.session, factory=self),
                'company_share': CompanyShareRepository(self.session, factory=self),
                'currency': CurrencyRepository(self.session, factory=self),
                'bond': BondRepository(self.session, factory=self),
                'index': IndexRepository(self.session, factory=self),
                'crypto': CryptoRepository(self.session, factory=self),
                'commodity': CommodityRepository(self.session, factory=self),  
                'cash': CashRepository(self.session, factory=self),
                'equity': EquityRepository(self.session, factory=self),
                'etf_share': ETFShareRepository(self.session, factory=self),  
                'share': ShareRepository(self.session, factory=self),
                'security': SecurityRepository(self.session, factory=self),
                'country': CountryRepository(self.session, factory=self),
                'continent': ContinentRepository(self.session, factory=self),
                'exchange': ExchangeRepository(self.session, factory=self)
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
            client = self.create_ibkr_client()
            return None

        if not self._ibkr_repositories:
            # Ensure local repositories exist first
            
            self._ibkr_repositories = {
                'factor': IBKRFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'factor_value': IBKRFactorValueRepository(
                    ibkr_client=client,
                    factory=self
                ),
                # Individual factor repositories
                'continent_factor': IBKRContinentFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'country_factor': IBKRCountryFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'index_factor': IBKRIndexFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'share_factor': IBKRShareFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'currency_factor': IBKRCurrencyFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'equity_factor': IBKREquityFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'index_future': IBKRIndexFutureRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'company_share': IBKRCompanyShareRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'currency': IBKRCurrencyRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'bond': IBKRBondRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'index': IBKRIndexRepository(
                    ibkr_client=client,
                    factory=self  
                ),
                'crypto': IBKRCryptoRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'commodity': IBKRCommodityRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'cash': IBKRCashRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'equity': IBKREquityRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'etf_share': IBKRETFShareRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'share': IBKRShareRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'security': IBKRSecurityRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'country': IBKRCountryRepository(ibkr_client=client,
                    factory=self),
                'continent': IBKRContinentRepository(ibkr_client=client,
                    factory=self),
                'exchange': IBKRExchangeRepository(
                    ibkr_client=client,
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
    
    
    @property
    def factor_value_local_repo(self):
        """Get factor_value repository for dependency injection."""
        return self._local_repositories.get('factor_value')


    @property
    def factor_local_repo(self):
        """Get factor repository for dependency injection."""
        return self._local_repositories.get('factor')

    # Individual local factor repositories
    @property
    def continent_factor_local_repo(self):
        """Get continent_factor repository for dependency injection."""
        return self._local_repositories.get('continent_factor')

    @property
    def country_factor_local_repo(self):
        """Get country_factor repository for dependency injection."""
        return self._local_repositories.get('country_factor')

    @property
    def index_factor_local_repo(self):
        """Get index_factor repository for dependency injection."""
        return self._local_repositories.get('index_factor')

    @property
    def currency_factor_local_repo(self):
        """Get currency_factor repository for dependency injection."""
        return self._local_repositories.get('currency_factor')

    @property
    def equity_factor_local_repo(self):
        """Get equity_factor repository for dependency injection."""
        return self._local_repositories.get('equity_factor')


    @property
    def base_factor_local_repo(self):
        """Get base_factor repository for dependency injection."""
        return self._local_repositories.get('base_factor')


    @property
    def share_factor_local_repo(self):
        """Get share_factor repository for dependency injection."""
        return self._local_repositories.get('share_factor')


    @property
    def index_future_local_repo(self):
        """Get index_future repository for dependency injection."""
        return self._local_repositories.get('index_future')


    @property
    def company_share_local_repo(self):
        """Get company_share repository for dependency injection."""
        return self._local_repositories.get('company_share')


    @property
    def currency_local_repo(self):
        """Get currency repository for dependency injection."""
        return self._local_repositories.get('currency')


    @property
    def bond_local_repo(self):
        """Get bond repository for dependency injection."""
        return self._local_repositories.get('bond')


    @property
    def index_local_repo(self):
        """Get index repository for dependency injection."""
        return self._local_repositories.get('index')


    @property
    def crypto_local_repo(self):
        """Get crypto repository for dependency injection."""
        return self._local_repositories.get('crypto')


    @property
    def commodity_local_repo(self):
        """Get commodity repository for dependency injection."""
        return self._local_repositories.get('commodity')


    @property
    def cash_local_repo(self):
        """Get cash repository for dependency injection."""
        return self._local_repositories.get('cash')


    @property
    def equity_local_repo(self):
        """Get equity repository for dependency injection."""
        return self._local_repositories.get('equity')


    @property
    def etf_share_local_repo(self):
        """Get etf_share repository for dependency injection."""
        return self._local_repositories.get('etf_share')


    @property
    def share_local_repo(self):
        """Get share repository for dependency injection."""
        return self._local_repositories.get('share')


    @property
    def security_local_repo(self):
        """Get security repository for dependency injection."""
        return self._local_repositories.get('security')

    @property
    def country_local_repo(self):
        """Get country repository for dependency injection."""
        return self._local_repositories.get('country')

    @property
    def continent_local_repo(self):
        """Get continent repository for dependency injection."""
        return self._local_repositories.get('continent')

    @property
    def exchange_local_repo(self):
        """Get exchange repository for dependency injection."""
        return self._local_repositories.get('exchange')


    @property
    def factor_ibkr_repo(self):
        """Get factor repository for dependency injection."""
        return self._ibkr_repositories.get('factor')


    @property
    def factor_value_ibkr_repo(self):
        """Get factor_value repository for dependency injection."""
        return self._ibkr_repositories.get('factor_value')

    # Individual IBKR factor repositories
    @property
    def continent_factor_ibkr_repo(self):
        """Get continent_factor repository for dependency injection."""
        return self._ibkr_repositories.get('continent_factor')

    @property
    def country_factor_ibkr_repo(self):
        """Get country_factor repository for dependency injection."""
        return self._ibkr_repositories.get('country_factor')

    @property
    def index_factor_ibkr_repo(self):
        """Get index_factor repository for dependency injection."""
        return self._ibkr_repositories.get('index_factor')

    @property
    def share_factor_ibkr_repo(self):
        """Get share_factor repository for dependency injection."""
        return self._ibkr_repositories.get('share_factor')

    @property
    def currency_factor_ibkr_repo(self):
        """Get currency_factor repository for dependency injection."""
        return self._ibkr_repositories.get('currency_factor')

    @property
    def equity_factor_ibkr_repo(self):
        """Get equity_factor repository for dependency injection."""
        return self._ibkr_repositories.get('equity_factor')


    @property
    def index_future_ibkr_repo(self):
        """Get index_future repository for dependency injection."""
        return self._ibkr_repositories.get('index_future')


    @property
    def company_share_ibkr_repo(self):
        """Get company_share repository for dependency injection."""
        return self._ibkr_repositories.get('company_share')


    @property
    def currency_ibkr_repo(self):
        """Get currency repository for dependency injection."""
        return self._ibkr_repositories.get('currency')


    @property
    def bond_ibkr_repo(self):
        """Get bond repository for dependency injection."""
        return self._ibkr_repositories.get('bond')


    @property
    def index_ibkr_repo(self):
        """Get index repository for dependency injection."""
        return self._ibkr_repositories.get('index')


    @property
    def crypto_ibkr_repo(self):
        """Get crypto repository for dependency injection."""
        return self._ibkr_repositories.get('crypto')


    @property
    def commodity_ibkr_repo(self):
        """Get commodity repository for dependency injection."""
        return self._ibkr_repositories.get('commodity')


    @property
    def cash_ibkr_repo(self):
        """Get cash repository for dependency injection."""
        return self._ibkr_repositories.get('cash')


    @property
    def equity_ibkr_repo(self):
        """Get equity repository for dependency injection."""
        return self._ibkr_repositories.get('equity')


    @property
    def etf_share_ibkr_repo(self):
        """Get etf_share repository for dependency injection."""
        return self._ibkr_repositories.get('etf_share')


    @property
    def share_ibkr_repo(self):
        """Get share repository for dependency injection."""
        return self._ibkr_repositories.get('share')


    @property
    def security_ibkr_repo(self):
        """Get security repository for dependency injection."""
        return self._ibkr_repositories.get('security')

    @property
    def country_ibkr_repo(self):
        """Get country repository for dependency injection."""
        return self._ibkr_repositories.get('country')

    @property
    def continent_ibkr_repo(self):
        """Get continent repository for dependency injection."""
        return self._ibkr_repositories.get('continent')

    @property
    def exchange_ibkr_repo(self):
        """Get exchange repository for dependency injection."""
        return self._ibkr_repositories.get('exchange')
