"""
IBKR Repository Provider - Interactive Brokers repository provider.

Handles registration of all IBKR-based repositories with the registry.
"""

from typing import Optional
from ..registry.repository_registry import RepositoryRegistry, RepositoryProvider

# Domain ports (interfaces)
from src.domain.ports.finance.instrument_port import InstrumentPort

# IBKR repository implementations
from ..ibkr_repo.finance.instrument_repository import IBKRInstrumentRepository
from ..ibkr_repo.finance.financial_assets.company_share_repository import IBKRCompanyShareRepository
from ..ibkr_repo.finance.company_repository import IBKRCompanyRepository
from ..ibkr_repo.finance.country_repository import IBKRCountryRepository
from ..ibkr_repo.finance.continent_repository import IBKRContinentRepository
from ..ibkr_repo.finance.exchange_repository import IBKRExchangeRepository
from ..ibkr_repo.finance.industry_repository import IBKRIndustryRepository
from ..ibkr_repo.finance.sector_repository import IBKRSectorRepository

# IBKR Factor repositories
from ..ibkr_repo.factor.ibkr_factor_repository import IBKRFactorRepository
from ..ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository
from ..ibkr_repo.factor.ibkr_instrument_factor_repository import IBKRInstrumentFactorRepository

# IBKR Financial asset repositories
from ..ibkr_repo.finance.financial_assets.bond_repository import IBKRBondRepository
from ..ibkr_repo.finance.financial_assets.cash_repository import IBKRCashRepository
from ..ibkr_repo.finance.financial_assets.commodity_repository import IBKRCommodityRepository
from ..ibkr_repo.finance.financial_assets.crypto_repository import IBKRCryptoRepository
from ..ibkr_repo.finance.financial_assets.currency_repository import IBKRCurrencyRepository
from ..ibkr_repo.finance.financial_assets.equity_repository import IBKREquityRepository
from ..ibkr_repo.finance.financial_assets.etf_share_repository import IBKRETFShareRepository
from ..ibkr_repo.finance.financial_assets.index_repository import IBKRIndexRepository
from ..ibkr_repo.finance.financial_assets.security_repository import IBKRSecurityRepository
from ..ibkr_repo.finance.financial_assets.share_repository import IBKRShareRepository

# Add imports for additional IBKR repositories as needed...


class IBKRRepositoryProvider(RepositoryProvider):
    """
    Repository provider for Interactive Brokers (IBKR) repositories.
    
    This provider creates and registers all IBKR repositories that interact
    with the Interactive Brokers API.
    """
    
    def __init__(self, registry: RepositoryRegistry, ibkr_client):
        """
        Initialize IBKR repository provider.
        
        Args:
            registry: The central repository registry
            ibkr_client: Interactive Brokers API client
        """
        super().__init__(registry)
        self.ibkr_client = ibkr_client
        self._repositories = {}
    
    def register_repositories(self) -> None:
        """Register all IBKR repositories with the registry."""
        if not self.ibkr_client:
            return  # Skip registration if no IBKR client available
        
        self._create_repositories()
        self._register_with_registry()
    
    def _create_repositories(self) -> None:
        """Create all IBKR repository instances."""
        # Core IBKR repositories
        self._repositories[IBKRInstrumentRepository] = IBKRInstrumentRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        
        # Geographic IBKR repositories
        self._repositories[IBKRCountryRepository] = IBKRCountryRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        self._repositories[IBKRContinentRepository] = IBKRContinentRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        self._repositories[IBKRExchangeRepository] = IBKRExchangeRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        self._repositories[IBKRIndustryRepository] = IBKRIndustryRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        self._repositories[IBKRSectorRepository] = IBKRSectorRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        
        # Financial IBKR repositories
        self._repositories[IBKRCompanyRepository] = IBKRCompanyRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        
        # Factor IBKR repositories
        self._repositories[IBKRFactorRepository] = IBKRFactorRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        self._repositories[IBKRFactorValueRepository] = IBKRFactorValueRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        self._repositories[IBKRInstrumentFactorRepository] = IBKRInstrumentFactorRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        
        # Financial asset IBKR repositories
        self._repositories[IBKRCompanyShareRepository] = IBKRCompanyShareRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        self._repositories[IBKRBondRepository] = IBKRBondRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        self._repositories[IBKRCashRepository] = IBKRCashRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        self._repositories[IBKRCommodityRepository] = IBKRCommodityRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        self._repositories[IBKRCryptoRepository] = IBKRCryptoRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        self._repositories[IBKRCurrencyRepository] = IBKRCurrencyRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        self._repositories[IBKREquityRepository] = IBKREquityRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        self._repositories[IBKRETFShareRepository] = IBKRETFShareRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        self._repositories[IBKRIndexRepository] = IBKRIndexRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        self._repositories[IBKRSecurityRepository] = IBKRSecurityRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        self._repositories[IBKRShareRepository] = IBKRShareRepository(
            ibkr_client=self.ibkr_client, factory=self
        )
        
        # TODO: Add more IBKR repositories as needed
        # This is a subset - you would add all your IBKR factor repositories,
        # options repositories, etc.
    
    def _register_with_registry(self) -> None:
        """Register all created IBKR repositories with the central registry."""
        for repo_type, instance in self._repositories.items():
            # IBKR repositories are registered by their concrete type
            # This allows differentiation from local repositories
            self.registry.register(repo_type, instance)
    
    def get_repository(self, repository_type):
        """Get IBKR repository by type (IBKR provider specific)."""
        return self._repositories.get(repository_type)
    
    @property
    def has_client(self) -> bool:
        """Check if IBKR client is available."""
        return self.ibkr_client is not None