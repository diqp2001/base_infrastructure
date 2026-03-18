"""
IBKR ETF Share Portfolio Company Share Repository - Interactive Brokers implementation for ETF Share Portfolio Company Shares.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.domain.ports.finance.financial_assets.etf_share_portfolio_company_share_port import ETFSharePortfolioCompanySharePort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.domain.entities.finance.financial_assets.share.etf_share_portfolio_company_share import ETFSharePortfolioCompanyShare
from src.infrastructure.repositories.mappers.finance.financial_assets.etf_share_portfolio_company_share_mapper import ETFSharePortfolioCompanyShareMapper


class IBKRETFSharePortfolioCompanyShareRepository(IBKRFinancialAssetRepository, ETFSharePortfolioCompanySharePort):
    """
    IBKR implementation of ETFSharePortfolioCompanySharePort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR ETF Share Portfolio Company Share Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client (InteractiveBrokersBroker instance)
            factory: Repository factory for dependency injection (preferred)
        """
        self.ib_broker = ibkr_client  # Use ib_broker for consistency with reference implementation
        
        self.factory = factory
        self.local_repo = self.factory.etf_share_portfolio_company_share_local_repo
        self.mapper = ETFSharePortfolioCompanyShareMapper()

    @property
    def entity_class(self):
        """Return the domain entity class for ETFSharePortfolioCompanyShare."""
        return ETFSharePortfolioCompanyShare

    def _create_or_get(self, symbol: str = None, **kwargs) -> Optional[ETFSharePortfolioCompanyShare]:
        """
        Get or create an ETF share portfolio company share by symbol using IBKR API.
        
        Args:
            symbol: The ETF ticker symbol (e.g., 'SPY', 'QQQ')
            
        Returns:
            ETFSharePortfolioCompanyShare entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            existing = self.local_repo.get_by_symbol(symbol)
            if existing:
                return existing
            
            # 2. Fetch from IBKR API
            contract = self._fetch_contract(symbol, **kwargs)
            if not contract:
                return None
                
            # 3. Get contract details from IBKR
            contract_details = self._fetch_contract_details(contract)
            if not contract_details:
                return None
                
            # 4. Apply IBKR-specific rules and convert to domain entity
            entity = self._contract_to_domain(contract, contract_details)
            if not entity:
                return None
                
            # 5. Delegate persistence to local repository
            return self.local_repo.add(entity)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for symbol {symbol}: {e}")
            return None

    def get_by_id(self, entity_id: int) -> Optional[ETFSharePortfolioCompanyShare]:
        """Get ETF share portfolio company share by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[ETFSharePortfolioCompanyShare]:
        """Get all ETF share portfolio company shares (delegates to local repository)."""
        return self.local_repo.get_all()

    def get_by_symbol(self, symbol: str) -> Optional[ETFSharePortfolioCompanyShare]:
        """Get ETF share portfolio company share by symbol (delegates to local repository)."""
        return self.local_repo.get_by_symbol(symbol)

    def get_by_exchange_id(self, exchange_id: int) -> List[ETFSharePortfolioCompanyShare]:
        """Get ETF share portfolio company shares by exchange ID (delegates to local repository)."""
        return self.local_repo.get_by_exchange_id(exchange_id)

    def get_by_currency_id(self, currency_id: int) -> List[ETFSharePortfolioCompanyShare]:
        """Get ETF share portfolio company shares by currency ID (delegates to local repository)."""
        return self.local_repo.get_by_currency_id(currency_id)

    def get_by_underlying_asset_id(self, underlying_asset_id: int) -> List[ETFSharePortfolioCompanyShare]:
        """Get ETF share portfolio company shares by underlying asset ID (delegates to local repository)."""
        return self.local_repo.get_by_underlying_asset_id(underlying_asset_id)

    def add(self, entity: ETFSharePortfolioCompanyShare) -> Optional[ETFSharePortfolioCompanyShare]:
        """Add ETF share portfolio company share entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: ETFSharePortfolioCompanyShare) -> ETFSharePortfolioCompanyShare:
        """Update ETF share portfolio company share entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete ETF share portfolio company share entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def _fetch_contract(self, symbol: str, **kwargs) -> Optional[Contract]:
        """
        Fetch contract from IBKR API.
        
        Args:
            symbol: ETF ticker symbol
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            contract.symbol = symbol.upper()
            contract.secType = "STK"  # ETFs are traded as stocks
            contract.exchange = "SMART"  # IBKR smart routing
            contract.currency = "USD"
            
            # Apply IBKR-specific contract setup
            contract = self._apply_ibkr_symbol_rules(contract, symbol)
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR contract for {symbol}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[ContractDetails]:
        """
        Fetch contract details from IBKR API.
        
        Args:
            contract: IBKR Contract object
            
        Returns:
            ContractDetails object or None if not found
        """
        try:
            # Use the broker's get_contract_details method
            contract_details = self.ib_broker.get_contract_details(contract, timeout=15)
            
            if contract_details and len(contract_details) > 0:
                return contract_details
            else:
                print(f"No contract details received for {contract.symbol}")
                return None
                
        except Exception as e:
            print(f"Error fetching IBKR ETF contract details: {e}_{os.path.abspath(__file__)}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details_list: List[dict]) -> Optional[ETFSharePortfolioCompanyShare]:
        """
        Convert IBKR contract and details directly to domain entity.
        
        Args:
            contract: IBKR Contract object
            contract_details_list: IBKR ContractDetails list
            
        Returns:
            ETFSharePortfolioCompanyShare domain entity or None if conversion failed
        """
        try:
            # Use the first contract details result
            contract_details = contract_details_list[0] if contract_details_list else {}
            
            # Extract data from IBKR API response
            symbol = contract.symbol
            name = contract_details.get('long_name', f"ETF Share Portfolio Company Share {symbol}")
            currency_iso_code = contract_details.get('currency', 'USD')
            
            # Get or create dependencies
            currency = self._get_or_create_currency(iso_code=currency_iso_code)
            exchange = self._get_or_create_exchange(contract_details.get("exchange"))
            
            return self.entity_class(
                id=None,  # Let database generate
                name=name,
                symbol=symbol,
                exchange_id=exchange.id if exchange else None,
                currency_id=currency.id if currency else None,
                underlying_asset_id=None  # Can be set later if needed
            )
        except Exception as e:
            print(f"Error converting IBKR ETF contract to domain entity: {e}_{os.path.abspath(__file__)}")
            return None

    def _get_or_create_exchange(self, exchange_code: str):
        """
        Get or create an exchange using factory or exchange repository if available.
        Falls back to direct exchange creation if no dependencies are provided.
        
        Args:
            exchange_code: Exchange code (e.g., 'NYSE', 'NASDAQ', 'ARCA')
            
        Returns:
            Exchange domain entity
        """
        try:
            # Try factory's exchange repository first (preferred approach)
            if self.factory and hasattr(self.factory, 'exchange_ibkr_repo'):
                exchange_repo = self.factory.exchange_ibkr_repo
                if exchange_repo:
                    exchange = exchange_repo._create_or_get(exchange_code)
                    if exchange:
                        return exchange
        except Exception as e:
            print(f"Error getting or creating exchange {exchange_code}: {e}_{os.path.abspath(__file__)}")
            # Return minimal exchange as last resort

    def _get_or_create_currency(self, iso_code: str, name: str = None):
        """
        Get or create a currency using factory or currency repository if available.
        Falls back to direct currency creation if no dependencies are provided.
        
        Args:
            iso_code: Currency ISO code (e.g., 'USD', 'EUR')
            name: Currency name (e.g., 'US Dollar')
            
        Returns:
            Currency domain entity
        """
        try:
            # Try factory's currency repository first (preferred approach)
            if self.factory and hasattr(self.factory, 'currency_ibkr_repo'):
                currency_repo = self.factory.currency_ibkr_repo
                if currency_repo:
                    currency = currency_repo._create_or_get(iso_code)
                    if currency:
                        return currency
        except Exception as e:
            print(f"Error getting or creating currency {iso_code}: {e}_{os.path.abspath(__file__)}")
            # Return minimal currency as last resort

    def _apply_ibkr_symbol_rules(self, contract: Contract, original_symbol: str) -> Contract:
        """Apply IBKR-specific symbol resolution and exchange rules for ETFs."""
        # Handle special cases for IBKR
        symbol = original_symbol.upper()
        
        # Set appropriate exchange based on symbol patterns for ETFs
        if symbol.endswith('.TO'):  # Toronto Stock Exchange
            contract.exchange = 'TSE'
            contract.currency = 'CAD'
            contract.symbol = symbol[:-3]  # Remove .TO suffix
        elif symbol.endswith('.L'):  # London Stock Exchange
            contract.exchange = 'LSE'
            contract.currency = 'GBP'
            contract.symbol = symbol[:-2]  # Remove .L suffix
        elif any(symbol.startswith(prefix) for prefix in ['NYSE:', 'NASDAQ:']):
            # Remove exchange prefix if present
            contract.symbol = symbol.split(':', 1)[1]
            
        return contract