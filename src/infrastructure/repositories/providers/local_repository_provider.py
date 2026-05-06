"""
Local Repository Provider - SQLAlchemy-based repository provider.

Handles registration of all local (SQLAlchemy) repositories with the registry.
"""

from typing import Optional
from sqlalchemy.orm import Session

from ..registry.repository_registry import RepositoryRegistry, RepositoryProvider

# Domain ports (interfaces)
from src.domain.ports.finance.instrument_port import InstrumentPort
from src.domain.ports.finance.financial_assets.financial_asset_port import FinancialAssetPort

# Local repository implementations
from ..local_repo.finance.instrument_repository import InstrumentRepository
from ..local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from ..local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
from ..local_repo.finance.company_repository import CompanyRepository
from ..local_repo.finance.position_repository import PositionRepository
from ..local_repo.finance.portfolio_repository import PortfolioRepository
from ..local_repo.geographic.sector_repository import SectorRepository
from ..local_repo.geographic.industry_repository import IndustryRepository
from ..local_repo.geographic.country_repository import CountryRepository
from ..local_repo.geographic.continent_repository import ContinentRepository
from ..local_repo.finance.exchange_repository import ExchangeRepository

# Factor repositories
from ..local_repo.factor.factor_repository import FactorRepository
from ..local_repo.factor.factor_value_repository import FactorValueRepository
from ..local_repo.factor.factor_dependency_repository import FactorDependencyRepository

# Financial asset repositories
from ..local_repo.finance.financial_assets.bond_repository import BondRepository
from ..local_repo.finance.financial_assets.cash_repository import CashRepository
from ..local_repo.finance.financial_assets.commodity_repository import CommodityRepository
from ..local_repo.finance.financial_assets.crypto_repository import CryptoRepository
from ..local_repo.finance.financial_assets.currency_repository import CurrencyRepository
from ..local_repo.finance.financial_assets.equity_repository import EquityRepository
from ..local_repo.finance.financial_assets.etf_share_repository import ETFShareRepository
from ..local_repo.finance.financial_assets.index_repository import IndexRepository
from ..local_repo.finance.financial_assets.security_repository import SecurityRepository
from ..local_repo.finance.financial_assets.share_repository import ShareRepository

# Add imports for additional repositories as needed...


class LocalRepositoryProvider(RepositoryProvider):
    """
    Repository provider for local SQLAlchemy-based repositories.
    
    This provider creates and registers all local repositories that use
    SQLAlchemy for persistence.
    """
    
    def __init__(self, registry: RepositoryRegistry, session: Session):
        """
        Initialize local repository provider.
        
        Args:
            registry: The central repository registry
            session: SQLAlchemy session for database operations
        """
        super().__init__(registry)
        self.session = session
        self._repositories = {}
    
    def register_repositories(self) -> None:
        """Register all local repositories with the registry."""
        self._create_repositories()
        self._register_with_registry()
    
    def _create_repositories(self) -> None:
        """Create all repository instances."""
        # Core repositories
        self._repositories[InstrumentPort] = InstrumentRepository(self.session, self)
        self._repositories[FinancialAssetPort] = FinancialAssetRepository(self.session, self)
        
        # Geographic repositories
        self._repositories[CountryRepository] = CountryRepository(self.session, self)
        self._repositories[ContinentRepository] = ContinentRepository(self.session, self)
        self._repositories[SectorRepository] = SectorRepository(self.session, self)
        self._repositories[IndustryRepository] = IndustryRepository(self.session, self)
        self._repositories[ExchangeRepository] = ExchangeRepository(self.session, self)
        
        # Financial repositories
        self._repositories[CompanyRepository] = CompanyRepository(self.session, self)
        self._repositories[PositionRepository] = PositionRepository(self.session, self)
        self._repositories[PortfolioRepository] = PortfolioRepository(self.session, self)
        
        # Factor repositories
        self._repositories[FactorRepository] = FactorRepository(self.session, self)
        self._repositories[FactorValueRepository] = FactorValueRepository(self.session, self)
        self._repositories[FactorDependencyRepository] = FactorDependencyRepository(self.session)
        
        # Financial asset repositories
        self._repositories[CompanyShareRepository] = CompanyShareRepository(self.session, self)
        self._repositories[BondRepository] = BondRepository(self.session, self)
        self._repositories[CashRepository] = CashRepository(self.session, self)
        self._repositories[CommodityRepository] = CommodityRepository(self.session, self)
        self._repositories[CryptoRepository] = CryptoRepository(self.session, self)
        self._repositories[CurrencyRepository] = CurrencyRepository(self.session, self)
        self._repositories[EquityRepository] = EquityRepository(self.session, self)
        self._repositories[ETFShareRepository] = ETFShareRepository(self.session, self)
        self._repositories[IndexRepository] = IndexRepository(self.session, self)
        self._repositories[SecurityRepository] = SecurityRepository(self.session, self)
        self._repositories[ShareRepository] = ShareRepository(self.session, self)
        
        # TODO: Add more repositories as needed
        # This is a subset - you would add all your factor repositories,
        # portfolio repositories, holding repositories, etc.
    
    def _register_with_registry(self) -> None:
        """Register all created repositories with the central registry."""
        for repo_type, instance in self._repositories.items():
            self.registry.register(repo_type, instance)
    
    def get_repository(self, repository_type):
        """Get repository by type (local provider specific)."""
        return self._repositories.get(repository_type)