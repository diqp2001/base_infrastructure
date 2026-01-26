"""
IBKR Future Repository - Interactive Brokers implementation for Futures.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.domain.ports.finance.financial_assets.derivatives.future.future_port import FuturePort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.domain.entities.finance.financial_assets.derivatives.future.future import Future
from src.domain.entities.finance.financial_assets.currency import Currency
from src.domain.entities.finance.exchange import Exchange
from src.domain.entities.country import Country
from src.domain.entities.continent import Continent


class IBKRFutureRepository(IBKRFinancialAssetRepository, FuturePort):
    """
    IBKR implementation of FuturePort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR Future Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client (InteractiveBrokersBroker instance)
            factory: Repository factory for dependency injection (preferred)
        """
        self.ib_broker = ibkr_client  # Use ib_broker for consistency with reference implementation
        
        self.factory = factory
        self.local_repo = self.factory.future_local_repo

    @property
    def entity_class(self):
        """Return the domain entity class for Future."""
        return Future

    def get_or_create(self, symbol: str, exchange: str = "CME", currency: str = "USD") -> Optional[Future]:
        """
        Get or create a future by symbol using IBKR API.
        Implements cascading creation: Future -> Currency/Exchange -> Country -> Continent
        
        Args:
            symbol: The future symbol (e.g., 'ES', 'CL', 'GC')
            exchange: Exchange code (default: CME)
            currency: Currency code (default: USD)
            
        Returns:
            Future entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            existing = self.local_repo.get_by_symbol(symbol)
            if existing:
                return existing
            
            # 2. Fetch from IBKR API
            contract = self._fetch_contract(symbol, exchange, currency)
            if not contract:
                return None
                
            # 3. Get contract details from IBKR
            contract_details_list = self._fetch_contract_details(contract)
            if not contract_details_list:
                return None
                
            # 4. Apply IBKR-specific rules and convert to domain entity
            entity = self._contract_to_domain(contract, contract_details_list, exchange, currency)
            if not entity:
                return None
                
            # 5. Delegate persistence to local repository
            return self.local_repo.add(entity)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for future symbol {symbol}: {e}")
            return None

    def get_by_symbol(self, symbol: str) -> Optional[Future]:
        """Get future by symbol (delegates to local repository)."""
        return self.local_repo.get_by_symbol(symbol)

    def get_by_id(self, entity_id: int) -> Optional[Future]:
        """Get future by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Future]:
        """Get all futures (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Future) -> Optional[Future]:
        """Add future entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Future) -> Optional[Future]:
        """Update future entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete future entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def _fetch_contract(self, symbol: str, exchange: str, currency: str) -> Optional[Contract]:
        """
        Create future contract using IBKR broker helper method.
        
        Args:
            symbol: Future symbol
            exchange: Exchange code
            currency: Currency code
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            # Use the broker's helper method to create future contract
            contract = self.ib_broker.create_future_contract(
                symbol=symbol.upper(),
                exchange=exchange,
                currency=currency
            )
            return contract
        except Exception as e:
            print(f"Error creating IBKR future contract for {symbol}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[List[dict]]:
        """
        Fetch future contract details from IBKR API using broker method.
        
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
            print(f"Error fetching IBKR future contract details: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details_list: List[dict], 
                           exchange: str, currency_code: str) -> Optional[Future]:
        """
        Convert IBKR contract and details to domain entity using real API data.
        Implements cascading creation chain: Future -> Currency/Exchange -> Country -> Continent
        
        Args:
            contract: IBKR Contract object
            contract_details_list: List of contract details dictionaries from IBKR API
            exchange: Exchange code
            currency_code: Currency code
            
        Returns:
            Future domain entity or None if conversion failed
        """
        try:
            # Use the first contract details result
            contract_details = contract_details_list[0] if contract_details_list else {}
            
            # Extract data from IBKR API response
            symbol = contract.symbol
            name = contract_details.get('long_name', f"{symbol} Future")
            
            # Get or create currency with cascading dependencies
            currency = self._get_or_create_currency(currency_code, self._get_currency_name(currency_code))
            
            # Get or create exchange with cascading dependencies
            exchange_entity = self._get_or_create_exchange(exchange, currency_code)
            
            return Future(
                id=None,  # Let database generate
                name=name,
                symbol=symbol,
                currency_id=currency.id if currency else 1,
                exchange_id=exchange_entity.id if exchange_entity else 1,
                underlying_asset_id=None,  # Would need to resolve underlying asset
                start_date=None,
                end_date=None
            )
        except Exception as e:
            print(f"Error converting IBKR future contract to domain entity: {e}")
            return None

    def _get_or_create_currency(self, iso_code: str, name: str) -> Currency:
        """
        Get or create a currency using factory or currency repository if available.
        Implements cascading creation: Currency -> Country -> Continent
        
        Args:
            iso_code: Currency ISO code (e.g., 'USD', 'EUR')
            name: Currency name (e.g., 'US Dollar')
            
        Returns:
            Currency domain entity
        """
        try:
            # Try factory's currency repository first (preferred approach)
            if self.factory and hasattr(self.factory, 'currency_local_repo'):
                currency_repo = self.factory.currency_local_repo
                if currency_repo:
                    # Check if currency exists
                    existing_currency = currency_repo.get_by_iso_code(iso_code)
                    if existing_currency:
                        return existing_currency
                    
                    # Currency doesn't exist, create with cascading dependencies
                    country = self._get_or_create_country_for_currency(iso_code)
                    
                    # Create new currency
                    new_currency = Currency(
                        id=None,  # Let database generate
                        name=name,
                        symbol=iso_code,
                        country_id=country.id if country else 1,  # Default to 1 if no country
                        start_date=None,
                        end_date=None
                    )
                    
                    return currency_repo.add(new_currency)
            
            # Fallback: create minimal currency if no repository available
            return Currency(
                id=None,
                name=name,
                symbol=iso_code,
                country_id=1,  # Default country
                start_date=None,
                end_date=None
            )
                    
        except Exception as e:
            print(f"Error getting or creating currency {iso_code}: {e}")
            # Return minimal currency as fallback
            return Currency(
                id=None,
                name=name,
                symbol=iso_code,
                country_id=1,
                start_date=None,
                end_date=None
            )

    def _get_or_create_exchange(self, exchange_code: str, currency_code: str = "USD") -> Exchange:
        """
        Get or create an exchange with cascading country/continent creation.
        
        Args:
            exchange_code: Exchange code (e.g., 'CME', 'CBOE')
            currency_code: Default currency code for the exchange
            
        Returns:
            Exchange domain entity
        """
        try:
            if self.factory and hasattr(self.factory, 'exchange_local_repo'):
                exchange_repo = self.factory.exchange_local_repo
                
                # Check if exchange exists
                existing_exchanges = exchange_repo.get_by_name(exchange_code)
                if existing_exchanges:
                    return existing_exchanges[0]  # Return first match
                
                # Exchange doesn't exist, create with cascading country
                country = self._get_or_create_country_for_exchange(exchange_code)
                
                # Map exchange codes to full names
                exchange_names = {
                    'CME': 'Chicago Mercantile Exchange',
                    'CBOE': 'Chicago Board Options Exchange',
                    'CBOT': 'Chicago Board of Trade',
                    'NYMEX': 'New York Mercantile Exchange',
                    'COMEX': 'Commodity Exchange',
                    'ICE': 'Intercontinental Exchange',
                    'EUREX': 'Eurex Exchange',
                }
                
                full_name = exchange_names.get(exchange_code, f"{exchange_code} Exchange")
                
                # Create new exchange
                return exchange_repo.get_or_create(
                    name=exchange_code,
                    legal_name=full_name,
                    country_id=country.id if country else 1
                )
            
            return None
            
        except Exception as e:
            print(f"Error getting or creating exchange {exchange_code}: {e}")
            return None

    def _get_or_create_country_for_currency(self, iso_code: str):
        """
        Get or create country for currency with cascading continent creation.
        Maps currency ISO codes to countries.
        
        Args:
            iso_code: Currency ISO code
            
        Returns:
            Country domain entity
        """
        try:
            # Map common currency codes to countries
            currency_to_country = {
                'USD': ('United States', 'US', 'North America'),
                'EUR': ('Eurozone', 'EU', 'Europe'),
                'GBP': ('United Kingdom', 'GB', 'Europe'),
                'JPY': ('Japan', 'JP', 'Asia'),
                'AUD': ('Australia', 'AU', 'Oceania'),
                'CAD': ('Canada', 'CA', 'North America'),
                'CHF': ('Switzerland', 'CH', 'Europe'),
                'CNY': ('China', 'CN', 'Asia'),
                'INR': ('India', 'IN', 'Asia')
            }
            
            country_name, iso_country_code, continent_name = currency_to_country.get(
                iso_code, ('Global', 'GL', 'Global')
            )
            
            if self.factory and hasattr(self.factory, 'country_local_repo'):
                country_repo = self.factory.country_local_repo
                
                # Check if country exists
                existing_country = country_repo.get_by_name(country_name)
                if existing_country:
                    return existing_country
                
                # Country doesn't exist, create with cascading continent
                continent = self._get_or_create_continent(continent_name)
                
                # Create new country
                return country_repo._create_or_get(
                    name=country_name,
                    iso_code=iso_country_code,
                    continent_id=continent.id if continent else 1
                )
            
            return None
            
        except Exception as e:
            print(f"Error getting or creating country for currency {iso_code}: {e}")
            return None

    def _get_or_create_country_for_exchange(self, exchange_code: str):
        """
        Get or create country for exchange with cascading continent creation.
        Maps exchange codes to countries.
        
        Args:
            exchange_code: Exchange code
            
        Returns:
            Country domain entity
        """
        try:
            # Map common exchange codes to countries
            exchange_to_country = {
                'CME': ('United States', 'US', 'North America'),
                'CBOE': ('United States', 'US', 'North America'),
                'CBOT': ('United States', 'US', 'North America'),
                'NYMEX': ('United States', 'US', 'North America'),
                'COMEX': ('United States', 'US', 'North America'),
                'ICE': ('United States', 'US', 'North America'),
                'EUREX': ('Germany', 'DE', 'Europe'),
                'LSE': ('United Kingdom', 'GB', 'Europe'),
                'JSE': ('Japan', 'JP', 'Asia'),
            }
            
            country_name, iso_country_code, continent_name = exchange_to_country.get(
                exchange_code, ('Global', 'GL', 'Global')
            )
            
            if self.factory and hasattr(self.factory, 'country_local_repo'):
                country_repo = self.factory.country_local_repo
                
                # Check if country exists
                existing_country = country_repo.get_by_name(country_name)
                if existing_country:
                    return existing_country
                
                # Country doesn't exist, create with cascading continent
                continent = self._get_or_create_continent(continent_name)
                
                # Create new country
                return country_repo._create_or_get(
                    name=country_name,
                    iso_code=iso_country_code,
                    continent_id=continent.id if continent else 1
                )
            
            return None
            
        except Exception as e:
            print(f"Error getting or creating country for exchange {exchange_code}: {e}")
            return None

    def _get_or_create_continent(self, continent_name: str):
        """
        Get or create continent.
        
        Args:
            continent_name: Continent name
            
        Returns:
            Continent domain entity
        """
        try:
            if self.factory and hasattr(self.factory, 'continent_local_repo'):
                continent_repo = self.factory.continent_local_repo
                
                # Check if continent exists
                existing_continent = continent_repo.get_by_name(continent_name)
                if existing_continent:
                    return existing_continent
                
                # Create new continent
                return continent_repo._create_or_get(
                    name=continent_name,
                    hemisphere=None,  # Could be mapped if needed
                    description=f"{continent_name} continent"
                )
            
            return None
            
        except Exception as e:
            print(f"Error getting or creating continent {continent_name}: {e}")
            return None

    def _get_currency_name(self, iso_code: str) -> str:
        """Get human-readable currency name from ISO code."""
        currency_names = {
            'USD': 'US Dollar',
            'EUR': 'Euro',
            'GBP': 'British Pound',
            'JPY': 'Japanese Yen',
            'AUD': 'Australian Dollar',
            'CAD': 'Canadian Dollar',
            'CHF': 'Swiss Franc',
            'CNY': 'Chinese Yuan',
            'INR': 'Indian Rupee'
        }
        return currency_names.get(iso_code, f"{iso_code} Currency")

    def get_major_futures(self) -> List[Future]:
        """Get major futures contracts from IBKR."""
        major_symbols = ['ES', 'NQ', 'YM', 'RTY', 'CL', 'GC', 'SI', 'NG']
        
        futures = []
        for symbol in major_symbols:
            future = self.get_or_create(symbol)
            if future:
                futures.append(future)
        
        return futures

    def get_equity_index_futures(self) -> List[Future]:
        """Get equity index futures."""
        equity_symbols = ['ES', 'NQ', 'YM', 'RTY']  # S&P, Nasdaq, Dow, Russell
        
        futures = []
        for symbol in equity_symbols:
            future = self.get_or_create(symbol)
            if future:
                futures.append(future)
        
        return futures

    def get_commodity_futures(self) -> List[Future]:
        """Get commodity futures."""
        commodity_symbols = ['CL', 'GC', 'SI', 'NG', 'HG', 'ZC', 'ZS', 'ZW']
        
        futures = []
        for symbol in commodity_symbols:
            future = self.get_or_create(symbol)
            if future:
                futures.append(future)
        
        return futures