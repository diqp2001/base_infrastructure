"""
IBKR ETF Share Portfolio Company Share Option Repository - Interactive Brokers implementation for ETF Share Portfolio Company Share Options.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.domain.ports.finance.financial_assets.derivatives.option.ETF_share_portfolio_company_share_option_port import ETFSharePortfolioCompanyShareOptionPort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.domain.entities.finance.financial_assets.derivatives.option.etf_share_portfolio_company_share_option import ETFSharePortfolioCompanyShareOption
from src.infrastructure.repositories.mappers.finance.financial_assets.etf_share_portfolio_company_share_option_mapper import ETFSharePortfolioCompanyShareOptionMapper


class IBKRETFSharePortfolioCompanyShareOptionRepository(IBKRFinancialAssetRepository,ETFSharePortfolioCompanyShareOptionPort):
    """
    IBKR implementation for ETF Share Portfolio Company Share Option operations.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR ETF Share Portfolio Company Share Option Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client (InteractiveBrokersBroker instance)
            factory: Repository factory for dependency injection (preferred)
        """
        self.ib_broker = ibkr_client  # Use ib_broker for consistency with reference implementation
        
        self.factory = factory
        self.local_repo = self.factory.etf_share_portfolio_company_share_option_local_repo
        self.mapper = ETFSharePortfolioCompanyShareOptionMapper()

    @property
    def entity_class(self):
        """Return the domain entity class for ETFSharePortfolioCompanyShareOption."""
        return ETFSharePortfolioCompanyShareOption

    def _create_or_get(self, symbol: str = None, **kwargs) -> Optional[ETFSharePortfolioCompanyShareOption]:
        """
        Get or create an ETF share portfolio company share option by symbol using IBKR API.
        
        Args:
            symbol: The option ticker symbol
            
        Returns:
            ETFSharePortfolioCompanyShareOption entity or None if creation/retrieval failed
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

    def get_by_id(self, option_id: int) -> Optional[ETFSharePortfolioCompanyShareOption]:
        """Get ETF share portfolio company share option by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(option_id)

    def get_all(self) -> List[ETFSharePortfolioCompanyShareOption]:
        """Get all ETF share portfolio company share options (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: ETFSharePortfolioCompanyShareOption) -> Optional[ETFSharePortfolioCompanyShareOption]:
        """Add ETF share portfolio company share option entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: ETFSharePortfolioCompanyShareOption) -> ETFSharePortfolioCompanyShareOption:
        """Update ETF share portfolio company share option entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, option_id: int) -> bool:
        """Delete ETF share portfolio company share option entity (delegates to local repository)."""
        return self.local_repo.delete(option_id)

    def _fetch_contract(self, symbol: str, **kwargs) -> Optional[Contract]:
        """
        Fetch contract from IBKR API.
        
        Args:
            symbol: Option ticker symbol or underlying symbol
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            contract.symbol = kwargs.get('underlying_symbol', symbol.split(' ')[0])
            contract.secType = "OPT"
            contract.exchange = kwargs.get('exchange', "SMART")  # IBKR smart routing
            contract.currency = kwargs.get('currency', "USD")
            
            # Set option-specific fields if provided
            if 'expiry' in kwargs:
                contract.lastTradeDateOrContractMonth = kwargs['expiry']
            if 'strike' in kwargs:
                contract.strike = float(kwargs['strike'])
            if 'right' in kwargs:
                contract.right = kwargs['right']  # 'C' for call, 'P' for put
            if 'multiplier' in kwargs:
                contract.multiplier = str(kwargs['multiplier'])
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR option contract for {symbol}: {e}")
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
            print(f"Error fetching IBKR option contract details: {e}_{os.path.abspath(__file__)}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details_list: List[dict]) -> Optional[ETFSharePortfolioCompanyShareOption]:
        """
        Convert IBKR contract and details directly to domain entity.
        
        Args:
            contract: IBKR Contract object
            contract_details_list: IBKR ContractDetails list
            
        Returns:
            ETFSharePortfolioCompanyShareOption domain entity or None if conversion failed
        """
        try:
            # Use the first contract details result
            contract_details = contract_details_list[0] if contract_details_list else {}
            
            # Extract data from IBKR API response
            symbol = contract_details.get('symbol', contract.symbol)
            name = contract_details.get('long_name', f"ETF Share Portfolio Company Share Option {symbol}")
            currency_iso_code = contract_details.get('currency', 'USD')
            
            # Get or create dependencies
            currency = self._get_or_create_currency(iso_code=currency_iso_code)
            exchange = self._get_or_create_exchange(contract_details.get("exchange"))
            
            return self.entity_class(
                id=None,  # Let database generate
                name=name,
                symbol=symbol,
                currency_id=currency.id if currency else None,
                underlying_asset_id=None,  # Can be set later if needed
                exchange_id=exchange.id if exchange else None,
                option_type=contract.right.lower() if hasattr(contract, 'right') else 'call',
                strike_price=Decimal(str(contract.strike)) if hasattr(contract, 'strike') and contract.strike else None,
                multiplier=int(contract.multiplier) if hasattr(contract, 'multiplier') and contract.multiplier else 100
            )
        except Exception as e:
            print(f"Error converting IBKR option contract to domain entity: {e}_{os.path.abspath(__file__)}")
            return None

    def _get_or_create_exchange(self, exchange_code: str):
        """
        Get or create an exchange using factory or exchange repository if available.
        
        Args:
            exchange_code: Exchange code (e.g., 'CBOE', 'ISE', 'PHLX')
            
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