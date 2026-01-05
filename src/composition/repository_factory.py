"""
Repository Factory - Composition root for IBKR repository architecture.

This module contains factory functions that create and configure repository
implementations based on the desired data source. The choice between local-only
and IBKR-backed repositories is made here at application startup.
"""

from typing import Optional
from sqlalchemy.orm import Session

from src.domain.ports.financial_assets.index_future_port import IndexFuturePort
from src.domain.ports.financial_assets.company_share_port import CompanySharePort
from src.domain.ports.financial_assets.currency_port import CurrencyPort
from src.domain.ports.financial_assets.bond_port import BondPort

from src.infrastructure.repositories.local_repo.finance.financial_assets.index_future_repository import IndexFutureRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.index_future_repository import IBKRIndexFutureRepository

from src.application.services.finance.financial_asset_service_v2 import FinancialAssetServiceV2


class RepositoryFactory:
    """
    Factory for creating repository implementations.
    
    This is the composition root where the decision between local-only
    and IBKR-backed repositories is made.
    """

    @staticmethod
    def create_local_repositories(session: Session) -> dict:
        """
        Create local-only repository configuration.
        
        Args:
            session: SQLAlchemy session for database operations
            
        Returns:
            Dictionary with repository implementations
        """
        return {
            'index_future': IndexFutureRepository(session),
            # Add other local repositories here as they're implemented
            # 'company_share': CompanyShareRepository(session),
            # 'currency': CurrencyRepository(session),
            # 'bond': BondRepository(session),
        }

    @staticmethod
    def create_ibkr_repositories(
        session: Session,
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
        local_repos = RepositoryFactory.create_local_repositories(session)
        
        # Wrap local repositories with IBKR implementations
        return {
            'index_future': IBKRIndexFutureRepository(
                ibkr_client=ibkr_client,
                local_repo=local_repos['index_future']
            ),
            # Add other IBKR repositories here as they're implemented
            # 'company_share': IBKRCompanyShareRepository(
            #     ibkr_client=ibkr_client,
            #     local_repo=local_repos['company_share']
            # ),
        }

    @staticmethod
    def create_financial_asset_service(
        session: Session,
        use_ibkr: bool = False,
        ibkr_client=None
    ) -> FinancialAssetServiceV2:
        """
        Create financial asset service with appropriate repository configuration.
        
        Args:
            session: SQLAlchemy session
            use_ibkr: Whether to use IBKR-backed repositories
            ibkr_client: IBKR client (required if use_ibkr=True)
            
        Returns:
            Configured FinancialAssetServiceV2 instance
        """
        if use_ibkr:
            if not ibkr_client:
                raise ValueError("IBKR client required when use_ibkr=True")
            repositories = RepositoryFactory.create_ibkr_repositories(session, ibkr_client)
        else:
            repositories = RepositoryFactory.create_local_repositories(session)

        # For now, we'll create stub implementations for missing ports
        # In a real implementation, you would have all repositories implemented
        return FinancialAssetServiceV2(
            index_future_port=repositories['index_future'],
            company_share_port=repositories.get('company_share', _create_stub_company_share_port()),
            currency_port=repositories.get('currency', _create_stub_currency_port()),
            bond_port=repositories.get('bond', _create_stub_bond_port())
        )


# Stub implementations for demonstration purposes
# In a real implementation, you would implement all the required repositories

class StubCompanySharePort(CompanySharePort):
    """Stub implementation for demonstration purposes."""
    
    def get_or_create(self, symbol: str):
        print(f"Stub: get_or_create company share {symbol}")
        return None
    
    def get_by_symbol(self, symbol: str):
        print(f"Stub: get_by_symbol company share {symbol}")
        return None
    
    def get_by_ticker(self, ticker: str):
        print(f"Stub: get_by_ticker company share {ticker}")
        return None
    
    def get_by_id(self, entity_id: int):
        return None
    
    def get_all(self):
        return []
    
    def add(self, entity):
        return None
    
    def update(self, entity):
        return None
    
    def delete(self, entity_id: int):
        return False


class StubCurrencyPort(CurrencyPort):
    """Stub implementation for demonstration purposes."""
    
    def get_or_create(self, symbol: str):
        print(f"Stub: get_or_create currency {symbol}")
        return None
    
    def get_by_symbol(self, symbol: str):
        print(f"Stub: get_by_symbol currency {symbol}")
        return None
    
    def get_by_iso_code(self, iso_code: str):
        print(f"Stub: get_by_iso_code currency {iso_code}")
        return None
    
    def get_by_id(self, entity_id: int):
        return None
    
    def get_all(self):
        return []
    
    def add(self, entity):
        return None
    
    def update(self, entity):
        return None
    
    def delete(self, entity_id: int):
        return False


class StubBondPort(BondPort):
    """Stub implementation for demonstration purposes."""
    
    def get_or_create(self, symbol: str):
        print(f"Stub: get_or_create bond {symbol}")
        return None
    
    def get_by_symbol(self, symbol: str):
        print(f"Stub: get_by_symbol bond {symbol}")
        return None
    
    def get_by_isin(self, isin: str):
        print(f"Stub: get_by_isin bond {isin}")
        return None
    
    def get_by_cusip(self, cusip: str):
        print(f"Stub: get_by_cusip bond {cusip}")
        return None
    
    def get_by_id(self, entity_id: int):
        return None
    
    def get_all(self):
        return []
    
    def get_by_maturity_range(self, start_date, end_date):
        return []
    
    def add(self, entity):
        return None
    
    def update(self, entity):
        return None
    
    def delete(self, entity_id: int):
        return False


def _create_stub_company_share_port() -> CompanySharePort:
    """Create stub company share port."""
    return StubCompanySharePort()


def _create_stub_currency_port() -> CurrencyPort:
    """Create stub currency port."""
    return StubCurrencyPort()


def _create_stub_bond_port() -> BondPort:
    """Create stub bond port."""
    return StubBondPort()