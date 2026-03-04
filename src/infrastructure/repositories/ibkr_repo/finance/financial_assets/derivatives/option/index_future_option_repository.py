"""
IBKR Index Future Option Repository - Interactive Brokers implementation for Index Future Options.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

import os
from typing import Any, Optional, List
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.infrastructure.repositories.mappers.finance.financial_assets.index_future_option_mapper import IndexFutureOptionMapper
from src.domain.ports.finance.financial_assets.derivatives.option.index_future_option_port import IndexFutureOptionPort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.domain.entities.finance.financial_assets.derivatives.option.index_future_option import IndexFutureOption
from src.domain.entities.finance.financial_assets.currency import Currency
from src.domain.entities.finance.exchange import Exchange


class IBKRIndexFutureOptionRepository(IBKRFinancialAssetRepository, IndexFutureOptionPort):
    """
    IBKR implementation of IndexFutureOptionPort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None, mapper: IndexFutureOptionMapper = None):
        """
        Initialize IBKR Index Future Option Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client (InteractiveBrokersBroker instance)
            factory: Repository factory for dependency injection (preferred)
            mapper: Option mapper for entity/model conversion (optional, will create if not provided)
        """
        self.ib_broker = ibkr_client  # Use ib_broker for consistency with reference implementation
        
        self.factory = factory
        self.local_repo = self.factory.index_future_option_local_repo 
        self.mapper = IndexFutureOptionMapper()

    @property
    def entity_class(self):
        """Return the domain entity class for IndexFutureOption."""
        return self.mapper.entity_class

    @property
    def model_class(self):
        return self.mapper.model_class

    def _create_or_get(self, symbol, strike_price: float = None, expiry: str = None, option_type: str = None) -> Optional[IndexFutureOption]:
        """
        Get or create an index future option by symbol and parameters using IBKR API.
        
        Args:
            symbol: The option symbol (e.g., 'ES', 'NQ')
            strike_price: Strike price of the option
            expiry: Expiry date (YYYYMMDD format)
            option_type: 'C' for call, 'P' for put
            
        Returns:
            IndexFutureOption entity or None if creation/retrieval failed
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
            
            # 2. Handle case where option parameters are not provided
            # This happens when called from factor creation pipelines
            if not strike_price or not expiry or not option_type:
                print(f"Warning: Option parameters not provided for {symbol}. Cannot create IBKR option contract without strike_price, expiry, and option_type.")
                print(f"Available parameters: strike_price={strike_price}, expiry={expiry}, option_type={option_type}")
                
                # Try to find any existing option for this symbol in local repo
                existing_options = self.local_repo.get_by_index_symbol(self._resolve_underlying_index(symbol))
                if existing_options:
                    print(f"Found {len(existing_options)} existing options for underlying {self._resolve_underlying_index(symbol)}")
                    # Return the first available option as fallback
                    return existing_options[0]
                
                # If no existing options, we cannot proceed without parameters
                print(f"No existing options found for {symbol} and insufficient parameters to create new option")
                return None
            
            # 3. Fetch from IBKR API with full parameters
            contract = self._fetch_option_contract(symbol, strike_price, expiry, option_type)
            if not contract:
                return None
                
            # 4. Get contract details from IBKR
            contract_details_list = self._fetch_contract_details(contract)
            if not contract_details_list:
                return None
            contract_detail = self.get_contract_by_local_symbol(contract_details_list, symbol)
            
            # 5. Apply IBKR-specific rules and convert to domain entity
            entity = self._contract_to_domain(contract, contract_detail)
            if not entity:
                return None
            return self.local_repo.add(entity)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for option {symbol}: {e}_{os.path.abspath(__file__)}")
            return None

    def get_contract_by_local_symbol(self, contract_details_list, symbol: str):
        return next(
            (contract for contract in contract_details_list
            if contract.get("local_symbol", "").startswith(symbol)),
            None
        )

    def get_by_symbol(self, symbol: str) -> Optional[IndexFutureOption]:
        """Get index future option by symbol (delegates to local repository)."""
        return self.local_repo.get_by_symbol(symbol)

    def get_by_symbol_and_strike(self, symbol: str, strike_price: float) -> Optional[IndexFutureOption]:
        """Get index future option by symbol and strike (delegates to local repository)."""
        return self.local_repo.get_by_symbol_and_strike(symbol, strike_price)

    def get_by_index_symbol(self, index_symbol: str) -> List[IndexFutureOption]:
        """Get all options for a specific index symbol (delegates to local repository)."""
        return self.local_repo.get_by_index_symbol(index_symbol)

    def get_by_id(self, entity_id: int) -> Optional[IndexFutureOption]:
        """Get index future option by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[IndexFutureOption]:
        """Get all index future options (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: IndexFutureOption) -> Optional[IndexFutureOption]:
        """Add index future option entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: IndexFutureOption) -> Optional[IndexFutureOption]:
        """Update index future option entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete index future option entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)
    def _extract_underlying_symbol(self, symbol: str) -> str:
        """Extract underlying symbol from future symbol (e.g., 'ESZ25' -> 'ES')."""
        # Remove month/year suffix
        return ''.join(c for c in symbol if c.isalpha())[:2]
    
    def _get_underlying_root_symbol(self, symbol: str) -> str:
        """
        Convert future symbol to underlying root symbol for options.
        
        Args:
            symbol: Future symbol like 'ESZ6', 'EW4', or already root like 'ES'
            
        Returns:
            Underlying root symbol for options (e.g., 'ES', 'RTY')
        """
        # Symbol mapping for common futures to their option underlying
        symbol_map = {
            'EW': 'RTY',     # E-mini Russell 2000 (EW future -> RTY options)
            'ES': 'ES',      # E-mini S&P 500  
            'NQ': 'NQ',      # E-mini NASDAQ
            'RTY': 'RTY',    # Already correct
            'YM': 'YM',      # E-mini Dow
        }
        
        # Extract the root symbol (remove month/year codes)
        root = self._extract_underlying_symbol(symbol)
        
        # Map to correct options symbol
        return symbol_map.get(root, root)
    
    def _get_option_exchange(self, underlying_symbol: str) -> str:
        """
        Get the appropriate exchange for futures options based on underlying.
        
        Args:
            underlying_symbol: Root symbol like 'ES', 'RTY'
            
        Returns:
            Exchange code for the options
        """
        exchange_map = {
            'ES': 'CME',     # E-mini S&P 500 options
            'NQ': 'CME',     # E-mini NASDAQ options
            'RTY': 'CME',    # E-mini Russell 2000 options
            'YM': 'CBOT',    # E-mini Dow options
        }
        return exchange_map.get(underlying_symbol, 'CME')
    
    def _get_option_multiplier(self, underlying_symbol: str) -> str:
        """
        Get the contract multiplier for futures options.
        
        Args:
            underlying_symbol: Root symbol like 'ES', 'RTY'
            
        Returns:
            Multiplier as string
        """
        multiplier_map = {
            'ES': '50',      # E-mini S&P 500 options
            'NQ': '20',      # E-mini NASDAQ options  
            'RTY': '50',     # E-mini Russell 2000 options
            'YM': '5',       # E-mini Dow options
        }
        return multiplier_map.get(underlying_symbol, '50')
    
    def _get_underlying_future_details(self, underlying_symbol: str, option_expiry: str) -> tuple[Optional[str], Optional[str]]:
        """
        Get the underlying future symbol and expiry for options.
        
        Args:
            underlying_symbol: Root symbol like 'ES', 'RTY'
            option_expiry: Option expiry in YYYYMMDD format
            
        Returns:
            Tuple of (future_symbol, future_expiry) or (None, None) if not determinable
        """
        try:
            # Convert option expiry to determine the corresponding future contract
            # For December 2026 options (20261218), the underlying future is ESZ6 (December 2026)
            
            if option_expiry and len(option_expiry) >= 6:
                year = int(option_expiry[:4])
                month = int(option_expiry[4:6])
                
                # Map month to future contract month code
                month_codes = {
                    1: 'F', 2: 'G', 3: 'H', 4: 'J', 5: 'K', 6: 'M',
                    7: 'N', 8: 'Q', 9: 'U', 10: 'V', 11: 'X', 12: 'Z'
                }
                
                month_code = month_codes.get(month)
                if month_code:
                    # Year digit (last digit of year)
                    year_digit = year % 10
                    
                    # Build future symbol: ES + month_code + year_digit (e.g., ESZ6)
                    future_symbol = f"{underlying_symbol}{month_code}{year_digit}"
                    
                    # Future expiry is typically the third Friday of the month
                    # For December 2026, that would be around 20261218
                    future_expiry = option_expiry  # Use same expiry for now
                    
                    return future_symbol, future_expiry
            
            return None, None
            
        except Exception as e:
            print(f"Error determining underlying future details: {e}")
            return None, None

    def build_future_contract_from_local_symbol(self,local_symbol: str) -> Contract:
        """
        Converts IBKR local_symbol like 'ESZ6'
        into a properly formatted IBKR FUT Contract.
        """
        MONTH_CODES = {
        "F": "01",  # January
        "G": "02",  # February
        "H": "03",  # March
        "J": "04",  # April
        "K": "05",  # May
        "M": "06",  # June
        "N": "07",  # July
        "Q": "08",  # August
        "U": "09",  # September
        "V": "10",  # October
        "X": "11",  # November
        "Z": "12",  # December
    }
        # Extract parts
        root_symbol = local_symbol[:-2]
        month_code = local_symbol[-2]
        year_digit = local_symbol[-1]

        if month_code not in MONTH_CODES:
            raise ValueError(f"Invalid month code: {month_code}")

        # Robust year handling (works across decades)
        current_year = datetime.utcnow().year
        current_decade = (current_year // 10) * 10
        year = current_decade + int(year_digit)

        # If decoded year is in the past, assume next decade
        if year < current_year - 1:
            year += 10

        expiry = f"{year}{MONTH_CODES[month_code]}"

        

        return expiry
    def _fetch_option_contract(self, symbol: str, strike_price: float, expiry: str, option_type: str) -> Optional[Contract]:
        """
        Fetch option contract from IBKR API.
        
        Args:
            symbol: Future symbol (e.g., 'ESZ6', 'EW4') or underlying root (e.g., 'ES', 'RTY')
            strike_price: Strike price
            expiry: Expiry date (YYYYMMDD format)
            option_type: 'C' for call, 'P' for put
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            
            # Convert future symbol to underlying root for options
            underlying_symbol = self._get_underlying_root_symbol(symbol)
            
            contract.symbol = underlying_symbol
            contract.secType = "FOP"  # Future Option
            contract.exchange = self._get_option_exchange(underlying_symbol)
            contract.currency = "USD"
            contract.strike = strike_price
            contract.right = option_type  # 'C' or 'P'
            contract.tradingClass = underlying_symbol  # Set trading class to underlying
            contract.multiplier = self._get_option_multiplier(underlying_symbol)
            contract.includeExpired = True
            
            # Generate proper local symbol and expiry based on IBKR format
            future_symbol, future_expiry = self._get_underlying_future_details(underlying_symbol, expiry)
            if future_symbol and future_expiry:
                # Format: "ESZ6 C6850" (future_symbol + space + option_type + strike)
                contract.localSymbol = f"{future_symbol} {option_type}{int(strike_price)}"
                # Use the underlying future's expiry, not the option expiry
                contract.lastTradeDateOrContractMonth = future_expiry
            else:
                # Fallback to direct expiry if we can't determine future details
                contract.lastTradeDateOrContractMonth = expiry
                # Don't set localSymbol if we can't generate it properly
                contract.localSymbol = ""
            
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
            print(f"Error fetching IBKR contract details: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details: Any) -> Optional[IndexFutureOption]:
        """
        Convert IBKR contract and details to domain entity.
        
        Args:
            contract: IBKR Contract object
            contract_details: Contract details dictionary from IBKR API
            
        Returns:
            IndexFutureOption domain entity or None if conversion failed
        """
        try:
            if not contract_details:
                print(f"No contract details available for conversion")
                return None
            
            # Apply IBKR-specific business rules and create domain entity
            underlying_index = self._resolve_underlying_index(contract.symbol)
            multiplier = contract_details.get('multiplier', '50')  # Default to 50 for ES options
            
            # Get or create currency and exchange dependencies
            currency = self._get_or_create_currency(contract_details.get("currency", "USD"), f"{contract_details.get('currency', 'USD')} Currency")
            exchange = self._get_or_create_exchange(contract_details.get("exchange", "CME"))
            underlying = self._get_or_create_underlying_index(underlying_index)
            
            return self.entity_class(
                id=None,
                name=f"{contract.symbol} Index Future Option",
                symbol=contract_details.get("local_symbol", contract.symbol),
                exchange_id=exchange.id if exchange else None,
                underlying_asset_id=underlying.id if underlying else None,
                currency_id=currency.id if currency else None,
                strike_price=Decimal(str(contract.strike)),
                multiplier=Decimal(str(multiplier)),
                index_symbol=underlying_index,
            )
        except Exception as e:
            print(f"Error converting IBKR option contract to domain entity: {e}_{os.path.abspath(__file__)}")
            return None

    def _get_or_create_currency(self, iso_code: str, name: str) -> Optional[Currency]:
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
            print(f"Error getting or creating currency {iso_code}: {e}")
            # Return minimal currency as last resort
           
    def _get_or_create_exchange(self, exchange_code: str) -> Optional[Exchange]:
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
            
    def _get_or_create_underlying_index(self, index_name: str) -> Optional[Exchange]:
        """
        Get or create an underlying index using factory or index repository.
        """
        try:
            if self.factory and hasattr(self.factory, 'index_ibkr_repo'):
                index_repo = self.factory.index_ibkr_repo
                if index_repo:
                    index = index_repo._create_or_get(index_name)
                    if index:
                        return index
            
        except Exception as e:
            print(f"Error getting or creating index {index_name}: {e}_{os.path.abspath(__file__)}")

    def _resolve_underlying_index(self, symbol: str) -> str:
        """Resolve underlying index from IBKR option symbol."""
        index_map = {
            'ES': 'SPX',      # S&P 500
            'NQ': 'NDX',      # NASDAQ 100
            'RTY': 'RUT',     # Russell 2000
            'YM': 'DJI'       # Dow Jones
        }
        return index_map.get(symbol, symbol)

    def get_option_chain(self, symbol: str, expiry: str = None) -> List[IndexFutureOption]:
        """
        Get option chain for a specific underlying and expiry.
        
        Args:
            symbol: Underlying symbol (e.g., 'ES')
            expiry: Optional expiry date filter
            
        Returns:
            List of IndexFutureOption entities for the chain
        """
        try:
            # For now, delegate to local repository
            # In future, could fetch live option chain from IBKR
            return self.local_repo.get_by_index_symbol(symbol)
            
        except Exception as e:
            print(f"Error getting option chain for {symbol}: {e}")
            return []

    def get_optimized_option_data(self, symbol: str, **kwargs) -> Optional[dict]:
        """
        Get option data with optimized settings to avoid 'thick data size'.
        
        Args:
            symbol: Option symbol
            **kwargs: Additional parameters for customization
            
        Returns:
            Option data with lightweight configuration
        """
        try:
            # Default lightweight configuration for options
            config = {
                'duration': kwargs.get('duration', '1 D'),  # 1 day for options
                'bar_size': kwargs.get('bar_size', '5 mins'),  # 5 minute bars
                'what_to_show': kwargs.get('what_to_show', 'TRADES'),  # Just trades
                'use_rth': kwargs.get('use_rth', True),  # Regular trading hours only
                'format_date': kwargs.get('format_date', 1)  # Simple date format
            }
            
            print(f"Requesting optimized option data for {symbol} with config: {config}")
            
            # Get the option entity first
            entity = self._create_or_get(symbol)
            if not entity:
                return None
                
            # Use the broker's historical data method with optimized settings
            if hasattr(self.ib_broker, 'get_historical_data'):
                # Create a lightweight contract for historical data request
                contract = self._fetch_option_contract(symbol, entity.strike_price, None, 'C')  # Default call
                if not contract:
                    return None
                    
                return self.ib_broker.get_historical_data(
                    contract=contract,
                    duration=config['duration'],
                    bar_size=config['bar_size'],
                    what_to_show=config['what_to_show'],
                    use_rth=config['use_rth'],
                    format_date=config['format_date']
                )
            else:
                print("Historical data method not available on broker")
                return None
                
        except Exception as e:
            print(f"Error getting optimized option data for {symbol}: {e}")
            return None