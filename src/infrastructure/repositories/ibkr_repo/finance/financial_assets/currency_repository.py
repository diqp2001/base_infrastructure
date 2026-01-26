"""
IBKR Currency Repository - Interactive Brokers implementation for Currencies.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.domain.entities.country import Country
from src.domain.ports.finance.financial_assets.currency_port import CurrencyPort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.domain.entities.finance.financial_assets.currency import Currency


class IBKRCurrencyRepository(IBKRFinancialAssetRepository, CurrencyPort):
    """
    IBKR implementation of CurrencyPort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR Currency Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client (InteractiveBrokersBroker instance)
            factory: Repository factory for dependency injection (preferred)
        """
        self.ib_broker = ibkr_client  # Use ib_broker for consistency with reference implementation
        
        self.factory = factory
        self.local_repo = self.factory.currency_local_repo
    @property
    def entity_class(self):
        """Return the domain entity class for Currency."""
        return Currency
    def get_or_create(self, symbol: str) -> Optional[Currency]:
        """
        Get or create a currency  by symbol using IBKR API.
        
        Args:
            symbol: The currency  symbol (e.g., 'USD', 'JPY')
            
        Returns:
            Currency entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            existing = self.local_repo.get_by_iso_code(symbol)
            if existing:
                return existing
            
            # 2. Fetch from IBKR API
            contract = self._fetch_contract(symbol)
            if not contract:
                return None
                
            # 3. Get contract details from IBKR
            contract_details_list = self._fetch_contract_details(contract)
            if not contract_details_list:
                return None
                
            # 4. Apply IBKR-specific rules and convert to domain entity
            entity = self._contract_to_domain(contract, contract_details_list, symbol)
            if not entity:
                return None
                
            # 5. Delegate persistence to local repository
            return self.local_repo.add(entity)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for currency pair {symbol}: {e}")
            return None

    def get_by_symbol(self, symbol: str) -> Optional[Currency]:
        """Get currency by symbol (delegates to local repository)."""
        return self.local_repo.get_by_symbol(symbol)

    def get_by_id(self, entity_id: int) -> Optional[Currency]:
        """Get currency by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Currency]:
        """Get all currencies (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Currency) -> Optional[Currency]:
        """Add currency entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Currency) -> Optional[Currency]:
        """Update currency entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete currency entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def _fetch_contract(self, symbol: str) -> Optional[Contract]:
        """
        Fetch currency contract from IBKR API.
        
        Args:
            pair_symbol: Currency pair symbol (e.g., 'EURUSD')
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            # Parse currency pair
            
            contract = Contract()
            contract.symbol = symbol
            contract.secType = "CASH"
            contract.exchange = "IDEALPRO"  
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR currency contract for {symbol}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[List[dict]]:
        """
        Fetch currency contract details from IBKR API using broker method.
        
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
            print(f"Error fetching IBKR currency contract details: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details_list: List[dict], pair_symbol: str) -> Optional[Currency]:
        """
        Convert IBKR contract and details to domain entity using real API data.
        
        Args:
            contract: IBKR Contract object
            contract_details_list: List of contract details dictionaries from IBKR API
            pair_symbol: Original pair symbol
            
        Returns:
            Currency domain entity or None if conversion failed
        """
        try:
            # Use the first contract details result
            contract_details = contract_details_list[0] if contract_details_list else {}
            
            base_currency, quote_currency = self._parse_currency_pair(pair_symbol)
            
            # Extract data from IBKR API response
            pip_size = contract_details.get('min_tick', 0.00001)
            long_name = contract_details.get('long_name', f"{base_currency}/{quote_currency}")
            country = self._get_or_create_country("USA")
            return Currency(
                id=None,  # Let database generate
                symbol=pair_symbol,
                name=long_name,
                country_id = country.id,
                start_date=datetime.today()
                # base_currency=base_currency,
                # quote_currency=quote_currency,
                # pip_size=Decimal(str(pip_size)),
                # # IBKR-specific fields  
                # ibkr_contract_id=contract_details.get('contract_id'),
                # ibkr_local_symbol=contract_details.get('local_symbol', ''),
                # ibkr_trading_class=contract_details.get('trading_class', ''),
                # ibkr_exchange=contract.exchange
            )
        except Exception as e:
            print(f"Error converting IBKR currency contract to domain entity: {e}")
            return None
        
    def _get_or_create_country(self,  name: str) -> Country:
        """
        Get or create a country using factory or country repository if available.
        Falls back to direct country creation if no dependencies are provided.
        
        Args:
            
            name: country name (e.g., 'USA')
            
        Returns:
            country domain entity
        """
        try:
            # Try factory's currency repository first (preferred approach)
            if self.factory and hasattr(self.factory, 'country_ibkr_repo'):
                country_repo = self.factory.country_ibkr_repo
                if country_repo:
                    country = country_repo.get_or_create(name)
                    if country:
                        return country
            
        except Exception as e:
            print(f"Error getting or creating currency {name}: {e}")
            

    def _parse_currency_pair(self, pair_symbol: str) -> tuple[str, str]:
        """
        Parse currency pair symbol into base and quote currencies.
        
        Args:
            pair_symbol: Currency pair (e.g., 'EURUSD', 'GBPJPY')
            
        Returns:
            Tuple of (base_currency, quote_currency)
        """
        if len(pair_symbol) != 6:
            raise ValueError(f"Invalid currency pair format: {pair_symbol}")
        
        base = pair_symbol[:3].upper()
        quote = pair_symbol[3:].upper()
        
        # Validate currency codes
        valid_currencies = {
            'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD', 
            'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'RUB', 'CNH',
            'HKD', 'SGD', 'ZAR', 'MXN', 'BRL', 'INR', 'KRW', 'TRY'
        }
        
        if base not in valid_currencies or quote not in valid_currencies:
            raise ValueError(f"Invalid currency codes in pair: {base}/{quote}")
        
        return base, quote

    def get_major_pairs(self) -> List[Currency]:
        """Get major currency pairs from IBKR."""
        major_pairs = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'USDCAD', 'AUDUSD', 'NZDUSD'
        ]
        
        currencies = []
        for pair in major_pairs:
            currency = self.get_or_create(pair)
            if currency:
                currencies.append(currency)
        
        return currencies