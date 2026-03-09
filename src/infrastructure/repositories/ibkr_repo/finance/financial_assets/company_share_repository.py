"""
IBKR Company Share Repository - Interactive Brokers implementation for Company Shares.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.domain.ports.finance.financial_assets.share.company_share.company_share_port import CompanySharePort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.infrastructure.repositories.mappers.finance.financial_assets.company_share_mapper import CompanyShareMapper



class IBKRCompanyShareRepository(IBKRFinancialAssetRepository, CompanySharePort):
    """
    IBKR implementation of CompanySharePort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR Company Share Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client (InteractiveBrokersBroker instance)
            factory: Repository factory for dependency injection (preferred)
            mapper: CompanyShare mapper for entity/model conversion (optional, will create if not provided)
        """
        self.ib_broker = ibkr_client  # Use ib_broker for consistency with reference implementation
        
        self.factory = factory
        self.local_repo = self.factory.company_share_local_repo
        self.mapper = CompanyShareMapper()

    @property
    def entity_class(self):
        """Return the domain entity class for CompanyShare."""
        return self.mapper.entity_class

    # Factor-related methods (delegated to factor repository)
    
    def get_or_create_factor_value_with_ticks(
        self, 
        symbol_or_name: str, 
        factor_id: int, 
        time: str,
        tick_data: Optional[Dict[int, Any]] = None
    ):
        """
        Get or create a factor value using the specialized factor repository.
        
        This method is now delegated to IBKRCompanyShareFactorRepository.
        """
        if not self.factor_repo:
            print("Factor repository not available")
            return None
        return self.factor_repo.get_or_create_factor_value_with_ticks(
            symbol_or_name, factor_id, time, tick_data
        )
    
    def create_factor_value_from_tick_data(self, symbol: str, tick_type, tick_value: Any, time: str):
        """
        Create a factor value from tick data using the specialized factor repository.
        
        This method is now delegated to IBKRCompanyShareFactorRepository.
        """
        if not self.factor_repo:
            print("Factor repository not available")
            return None
        return self.factor_repo.create_factor_value_from_tick_data(
            symbol, tick_type, tick_value, time
        )

    def get_or_create_factor_value(self, symbol_or_name: str, factor_id: int, time: str):
        """
        Get or create a factor value using the specialized factor repository.
        
        This method is now delegated to IBKRCompanyShareFactorRepository.
        """
        if not self.factor_repo:
            print("Factor repository not available")
            return None
        return self.factor_repo.get_or_create_factor_value(symbol_or_name, factor_id, time)
        


    def _create_or_get(self, symbol: str=None,**kwargs) -> Optional[CompanyShare]:
        """
        Get or create a company share by symbol using IBKR API.
        
        Args:
            symbol: The stock ticker symbol (e.g., 'AAPL', 'MSFT')
            
        Returns:
            CompanyShare entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            existing = self.local_repo.get_by_symbol(symbol)
            if existing:
                return existing
            
            # 2. Fetch from IBKR API
            contract = self._fetch_contract(symbol,**kwargs)
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

    def get_by_ticker(self, ticker: str) -> List[CompanyShare]:
        """Get company share by ticker (delegates to local repository)."""
        return self.local_repo.get_by_ticker(ticker)

    def get_by_id(self, entity_id: int) -> Optional[CompanyShare]:
        """Get company share by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[CompanyShare]:
        """Get all company shares (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: CompanyShare) -> Optional[CompanyShare]:
        """Add company share entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity_id: int, **kwargs) -> Optional[CompanyShare]:
        """Update company share entity (delegates to local repository)."""
        return self.local_repo.update(entity_id, **kwargs)

    def delete(self, entity_id: int) -> bool:
        """Delete company share entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def exists_by_ticker(self, ticker: str) -> bool:
        """Check if company share exists by ticker (delegates to local repository)."""
        return self.local_repo.exists_by_ticker(ticker)

    def get_by_company_id(self, company_id: int) -> List[CompanyShare]:
        """Get company shares by company ID (delegates to local repository)."""
        return self.local_repo.get_by_company_id(company_id)

    def get_by_exchange_id(self, exchange_id: int) -> List[CompanyShare]:
        """Get company shares by exchange ID (delegates to local repository)."""
        return self.local_repo.get_by_exchange_id(exchange_id)

    def get_active_company_shares(self) -> List[CompanyShare]:
        """Get all active company shares (delegates to local repository)."""
        return self.local_repo.get_active_company_shares()

    def _fetch_contract(self, symbol: str) -> Optional[Contract]:
        """
        Fetch contract from IBKR API.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            contract.symbol = symbol.upper()
            contract.secType = "STK"
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
            # Use the broker's get_contract_details method (like in reference implementation)
            contract_details = self.ib_broker.get_contract_details(contract, timeout=15)
            
            if contract_details and len(contract_details) > 0:
                return contract_details
            else:
                print(f"No contract details received for {contract.symbol}")
                return None
                
        except Exception as e:
            print(f"Error fetching IBKR index contract details: {e}_{os.path.abspath(__file__)}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details_list: List[dict]) -> Optional[CompanyShare]:
        """
        Convert IBKR contract and details directly to domain entity.
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object
            
        Returns:
            CompanyShare domain entity or None if conversion failed
        """
        
        try:
            # Use the first contract details result
            contract_details = contract_details_list[0] if contract_details_list else {}
            
            # Extract data from IBKR API response
            symbol = contract.symbol
            name = contract_details.get('long_name', f"{symbol}")
            currency_iso_code =  contract_details.get('currency')
            # Get or create USD currency for indices (most indices are USD-denominated)
            currency = self._get_or_create_currency(iso_code = currency_iso_code)
            exchange=self._get_or_create_exchange(contract_details.get("exchange"))
            company=self._get_or_create_company(contract.symbol)
            
            return self.entity_class(
                id=None,  # Let database generate
                name=name,
                symbol=symbol,
                currency_id=currency.id,
                exchange_id=exchange.id,
                company_id=company.id,
            )
        except Exception as e:
            print(f"Error converting IBKR index contract to domain entity: {e}_{os.path.abspath(__file__)}")
            return None
    def _get_or_create_company(self, name: str):
        """
        
        """
        try:
            # Try factory's exchange repository first (preferred approach)
            if self.factory and hasattr(self.factory, 'company_ibkr_repo'):
                company_repo = self.factory.company_ibkr_repo
                if company_repo:
                    company = company_repo._create_or_get(name)
                    if company:
                        return company
            
           
                    
        except Exception as e:
            print(f"Error getting or creating exchange {name}: {e}_{os.path.abspath(__file__)}")
            # Return minimal exchange as last resort   
    def _get_or_create_exchange(self, exchange_code: str):
        """
        Get or create an exchange using factory or exchange repository if available.
        Falls back to direct exchange creation if no dependencies are provided.
        
        Args:
            exchange_code: Exchange code (e.g., 'CME', 'GLOBEX', 'NYSE')
            
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
        
    def _get_or_create_currency(self, iso_code: str, name: str = None) :
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
        """Apply IBKR-specific symbol resolution and exchange rules."""
        # Handle special cases for IBKR
        symbol = original_symbol.upper()
        
        # Map common symbols to IBKR equivalents
        ibkr_symbol_map = {
            'BRK.A': 'BRK A',  # Berkshire Hathaway Class A
            'BRK.B': 'BRK B',  # Berkshire Hathaway Class B
        }
        
        contract.symbol = ibkr_symbol_map.get(symbol, symbol)
        
        # Set appropriate exchange based on symbol patterns
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

    def _resolve_exchange_id(self, ibkr_exchange: str, contract_details: ContractDetails) -> int:
        """Resolve exchange ID from IBKR exchange code using factory pattern."""
        try:
            exchange_local_repo = self.factory.exchange_local_repo
            
            # Map IBKR exchange codes to standard names
            exchange_name_map = {
                'SMART': 'SMART',
                'NASDAQ': 'NASDAQ',
                'NYSE': 'NYSE',
                'TSE': 'TSE',
                'LSE': 'LSE',
            }
            
            exchange_name = exchange_name_map.get(ibkr_exchange, ibkr_exchange)
            exchange_object = exchange_local_repo.get_or_create(exchange_name)
            
            return exchange_object.id if exchange_object else 1
        except Exception as e:
            print(f"Error resolving exchange ID for {ibkr_exchange}: {e}")
            return 1

    def _resolve_company_id(self, symbol: str, contract_details: ContractDetails) -> int:
        """Resolve company ID from IBKR data using factory pattern."""
        try:
            company_local_repo = self.factory.company_local_repo
            
            # Extract company name from contract details
            company_name = getattr(contract_details, 'longName', f"{symbol} Company")
            
            # Create or get company
            company_object = company_local_repo.get_or_create(company_name)
            
            return company_object.id if company_object else 1
        except Exception as e:
            print(f"Error resolving company ID for {symbol}: {e}")
            return 1
    
