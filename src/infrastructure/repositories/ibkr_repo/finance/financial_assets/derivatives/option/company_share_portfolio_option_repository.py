"""
IBKR Portfolio Company Share Option Repository - Interactive Brokers implementation for Portfolio Company Share Options.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.domain.ports.finance.financial_assets.derivatives.option.company_share_portfolio_option_port import CompanySharePortfolioOptionPort

from src.domain.entities.finance.financial_assets.derivatives.option.company_share_portfolio_option import CompanySharePortfolioOption
from src.infrastructure.repositories.mappers.finance.financial_assets.company_share_portfolio_option_mapper import CompanySharePortfolioOptionMapper


class IBKRCompanySharePortfolioOptionRepository(IBKRFinancialAssetRepository, CompanySharePortfolioOptionPort):
    """
    IBKR implementation of PortfolioCompanyShareOptionPort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR Portfolio Company Share Option Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client (InteractiveBrokersBroker instance)
            factory: Repository factory for dependency injection (preferred)
        """
        self.ib_broker = ibkr_client  # Use ib_broker for consistency with reference implementation
        
        self.factory = factory
        self.local_repo = self.factory.portfolio_company_share_option_local_repo
        self.mapper = CompanySharePortfolioOptionMapper()

    @property
    def entity_class(self):
        """Return the domain entity class for PortfolioCompanyShareOption."""
        return CompanySharePortfolioOption

    def _create_or_get(self, symbol: str = None, strike_price: float = None, expiry: str = None, option_type: str = None, **kwargs) -> Optional[CompanySharePortfolioOption]:
        """
        Get or create a portfolio company share option by symbol and parameters using IBKR API.
        
        Args:
            symbol: The option symbol or ticker
            strike_price: Strike price of the option (optional)
            expiry: Expiry date (YYYYMMDD format, optional)
            option_type: 'C' for call, 'P' for put (optional)
            **kwargs: Additional parameters for customization
            
        Returns:
            PortfolioCompanyShareOption entity or None if creation/retrieval failed
        """
        try:
            # Validate that symbol is not a dictionary (common error)
            if isinstance(symbol, dict):
                print(f"Error: symbol parameter cannot be a dictionary. Received: {symbol}")
                print("This indicates the entity service is not properly extracting the symbol from configuration.")
                return None
            
            # Ensure symbol is a string
            if not isinstance(symbol, str):
                print(f"Error: symbol must be a string, got {type(symbol)}: {symbol}")
                return None
            
            # 1. Check local repository first
            existing = self.local_repo.get_by_symbol(symbol)
            if existing:
                return existing
            
            # 2. Fetch from IBKR API with enhanced parameters
            contract = self._fetch_contract(symbol, strike_price=strike_price, expiry=expiry, option_type=option_type, **kwargs)
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
            print(f"Error in IBKR get_or_create for symbol {symbol}: {e}_{os.path.abspath(__file__)}")
            return None

    def get_by_id(self, option_id: int) -> Optional[CompanySharePortfolioOption]:
        """Get portfolio company share option by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(option_id)

    def get_all(self) -> List[CompanySharePortfolioOption]:
        """Get all portfolio company share options (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: CompanySharePortfolioOption) -> Optional[CompanySharePortfolioOption]:
        """Add portfolio company share option entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: CompanySharePortfolioOption) -> CompanySharePortfolioOption:
        """Update portfolio company share option entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, option_id: int) -> bool:
        """Delete portfolio company share option entity (delegates to local repository)."""
        return self.local_repo.delete(option_id)

    def _fetch_contract(self, symbol: str, strike_price: float = None, expiry: str = None, option_type: str = None, **kwargs) -> Optional[Contract]:
        """
        Fetch contract from IBKR API with enhanced parameter handling.
        
        Args:
            symbol: Option ticker symbol or underlying symbol
            strike_price: Strike price of the option
            expiry: Expiry date (YYYYMMDD format)
            option_type: 'C' for call, 'P' for put
            **kwargs: Additional parameters
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            
            # Enhanced symbol handling
            underlying_symbol = kwargs.get('underlying_symbol', symbol.split(' ')[0] if ' ' in symbol else symbol)
            contract.symbol = underlying_symbol
            contract.secType = "OPT"
            contract.exchange = kwargs.get('exchange', "SMART")  # IBKR smart routing
            contract.currency = kwargs.get('currency', "USD")
            contract.includeExpired = kwargs.get('include_expired', True)
            
            # Set option-specific fields with priority to direct parameters
            if expiry or 'expiry' in kwargs:
                contract.lastTradeDateOrContractMonth = expiry or kwargs['expiry']
            if strike_price is not None or 'strike' in kwargs:
                contract.strike = strike_price if strike_price is not None else float(kwargs['strike'])
            if option_type or 'right' in kwargs:
                contract.right = option_type or kwargs['right']  # 'C' for call, 'P' for put
            if 'multiplier' in kwargs:
                contract.multiplier = str(kwargs['multiplier'])
            
            # Set trading class for better identification
            if 'trading_class' in kwargs:
                contract.tradingClass = kwargs['trading_class']
            else:
                contract.tradingClass = underlying_symbol
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR option contract for {symbol}: {e}_{os.path.abspath(__file__)}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[List[dict]]:
        """
        Fetch contract details from IBKR API using broker method.
        
        Args:
            contract: IBKR Contract object
            
        Returns:
            List of contract details dictionaries or None if not found
        """
        try:
            # Use the broker's get_contract_details method (like in reference implementation)
            contract_details = self.ib_broker.get_contract_details(contract, timeout=15)
            
            if contract_details and len(contract_details) > 0:
                return contract_details
            else:
                print(f"No contract details received for {contract.symbol}")
                return None
                
        except Exception as e:
            print(f"Error fetching IBKR contract details: {e}_{os.path.abspath(__file__)}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details_list: List[dict]) -> Optional[CompanySharePortfolioOption]:
        """
        Convert IBKR contract and details directly to domain entity.
        
        Args:
            contract: IBKR Contract object
            contract_details_list: IBKR ContractDetails list
            
        Returns:
            PortfolioCompanyShareOption domain entity or None if conversion failed
        """
        try:
            # Use the first contract details result
            contract_details = contract_details_list[0] if contract_details_list else {}
            
            # Extract data from IBKR API response
            symbol = contract_details.get('symbol', contract.symbol)
            name = contract_details.get('long_name', f"Portfolio Company Share Option {symbol}")
            currency_iso_code = contract_details.get('currency', 'USD')
            
            # Get or create dependencies
            currency = self._get_or_create_currency(iso_code=currency_iso_code)
            exchange = self._get_or_create_exchange(contract_details.get("exchange"))
            
            return self.entity_class(
                id=None,  # Let database generate
                name=name,
                symbol=symbol,
                currency_id=currency.id if currency and hasattr(currency, 'id') else None,
                underlying_asset_id=None,  # Can be set later if needed
                option_type=contract.right.lower() if hasattr(contract, 'right') else 'call'
            )
        except Exception as e:
            print(f"Error converting IBKR option contract to domain entity: {e}_{os.path.abspath(__file__)}")
            return None

    def _get_or_create_exchange(self, exchange_code: str):
        """
        Get or create an exchange using factory or exchange repository if available.
        Falls back to direct exchange creation if no dependencies are provided.
        
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