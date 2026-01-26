"""
IBKR Index Future Repository - Interactive Brokers implementation for Index Futures.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.domain.ports.finance.financial_assets.derivatives.future.index_future_port import IndexFuturePort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture
from src.domain.entities.finance.financial_assets.currency import Currency
from src.domain.entities.finance.exchange import Exchange
from src.infrastructure.repositories.mappers.finance.financial_assets.future_mapper import FutureMapper



class IBKRIndexFutureRepository(IBKRFinancialAssetRepository,IndexFuturePort):
    """
    IBKR implementation of IndexFuturePort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None, mapper: FutureMapper = None):
        """
        Initialize IBKR Index Future Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client (InteractiveBrokersBroker instance)
            factory: Repository factory for dependency injection (preferred)
            mapper: Future mapper for entity/model conversion (optional, will create if not provided)
        """
        self.ib_broker = ibkr_client  # Use ib_broker for consistency with reference implementation
        
        self.factory = factory
        self.local_repo =  self.factory.index_future_local_repo 
        self.mapper = mapper or FutureMapper()
    @property
    def entity_class(self):
        """Return the domain entity class for IndexFuture."""
        return IndexFuture
    def get_or_create(self, symbol: str) -> Optional[IndexFuture]:
        """
        Get or create an index future by symbol using IBKR API.
        
        Args:
            symbol: The future symbol (e.g., 'ESZ25', 'NQH25')
            
        Returns:
            IndexFuture entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            existing = self.local_repo.get_by_symbol(symbol)
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
            entity = self._contract_to_domain(contract, contract_details_list)
            if not entity:
                return None
                
            # 5. Delegate persistence to local repository
            return self.local_repo.add(entity)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for symbol {symbol}: {e}")
            return None

    def get_by_symbol(self, symbol: str) -> Optional[IndexFuture]:
        """Get index future by symbol (delegates to local repository)."""
        return self.local_repo.get_by_symbol(symbol)

    def get_by_id(self, entity_id: int) -> Optional[IndexFuture]:
        """Get index future by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[IndexFuture]:
        """Get all index futures (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: IndexFuture) -> Optional[IndexFuture]:
        """Add index future entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: IndexFuture) -> Optional[IndexFuture]:
        """Update index future entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete index future entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def _fetch_contract(self, symbol: str) -> Optional[Contract]:
        """
        Fetch contract from IBKR API.
        
        Args:
            symbol: Future symbol
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            contract.symbol = self._extract_underlying_symbol(symbol)
            contract.secType = "FUT"
            contract.exchange = "CME"  # Default for index futures
            contract.currency = "USD"
            contract.lastTradeDateOrContractMonth = self._extract_expiry_from_symbol(symbol)
            
            # Additional IBKR-specific contract setup
            contract = self._apply_ibkr_symbol_rules(contract, symbol)
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR contract for {symbol}: {e}")
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

    def _contract_to_domain(self, contract: Contract, contract_details_list: List[dict]) -> Optional[IndexFuture]:
        """
        Convert IBKR contract and details to domain entity using real API data.
        
        Args:
            contract: IBKR Contract object
            contract_details_list: List of contract details dictionaries from IBKR API
            
        Returns:
            IndexFuture domain entity or None if conversion failed
        """
        try:
            # Use the first contract details result
            contract_details = contract_details_list[0] if contract_details_list else {}
            
            # Apply IBKR-specific business rules and create domain entity
            underlying_index = self._resolve_underlying_index(contract.symbol)
            contract_size = self._resolve_contract_size(contract.symbol)
            tick_size = contract_details.get('min_tick', 0.25)
            
            # Get or create currency and exchange dependencies
            currency = self._get_or_create_currency(contract.currency, f"{contract.currency} Currency")
            exchange = self._get_or_create_exchange(contract.exchange)
            
            return IndexFuture(
                symbol=self._normalize_symbol(contract),
                #name=f"{self._normalize_symbol(contract)} Index Future",
                exchange_id=exchange.id if exchange else None,
                currency_id=currency.id if currency else None,
                underlying_asset=underlying_index,
                #contract_size=contract_size,
                #tick_size=Decimal(str(tick_size)),
                expiration_date=self._parse_expiry_date(contract.lastTradeDateOrContractMonth),
                #market_sector="INDEX",
                #asset_class="DERIVATIVE",
                # Additional IBKR-specific fields
                #ibkr_contract_id=getattr(contract, 'conId', None),
                #ibkr_local_symbol=getattr(contract, 'localSymbol', ''),
                #ibkr_trading_class=getattr(contract, 'tradingClass', '')
            )
        except Exception as e:
            print(f"Error converting IBKR contract to domain entity: {e}")
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
                    currency = currency_repo.get_or_create(iso_code)
                    if currency:
                        return currency
            
            # Fallback: create minimal currency entity for basic functionality
            return Currency(
                id=None,  # Let database generate
                symbol=iso_code,
                name=name,
                country_id=None,  # Will be set by currency repo if available
                start_date=datetime.today().date()
            )
                    
        except Exception as e:
            print(f"Error getting or creating currency {iso_code}: {e}")
            # Return minimal currency as last resort
            return Currency(
                id=None,
                symbol=iso_code,
                name=name,
                country_id=None,
                start_date=datetime.today().date()
            )

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
                    exchange = exchange_repo.get_or_create(exchange_code)
                    if exchange:
                        return exchange
            
            # Fallback: create minimal exchange entity for basic functionality
            return Exchange(
                id=None,  # Let database generate
                code=exchange_code,
                name=f"{exchange_code} Exchange",
                country_id=None,  # Will be set by exchange repo if available
                timezone="UTC",
                currency="USD"
            )
                    
        except Exception as e:
            print(f"Error getting or creating exchange {exchange_code}: {e}")
            # Return minimal exchange as last resort
            return Exchange(
                id=None,
                code=exchange_code,
                name=f"{exchange_code} Exchange", 
                country_id=None,
                timezone="UTC",
                currency="USD"
            )

    def _extract_underlying_symbol(self, symbol: str) -> str:
        """Extract underlying symbol from future symbol (e.g., 'ESZ25' -> 'ES')."""
        # Remove month/year suffix
        return ''.join(c for c in symbol if c.isalpha())[:2]

    def _extract_expiry_from_symbol(self, symbol: str) -> str:
        """Extract expiry from symbol (e.g., 'ESZ25' -> '202512')."""
        # This is simplified - real implementation would handle month codes and years
        month_code = ''.join(c for c in symbol if c.isalpha())[-1:]
        year = ''.join(c for c in symbol if c.isdigit())
        
        # Convert month code to number (simplified)
        month_map = {'H': '03', 'M': '06', 'U': '09', 'Z': '12'}
        month = month_map.get(month_code, '12')
        
        return f"20{year}{month}"

    def _apply_ibkr_symbol_rules(self, contract: Contract, original_symbol: str) -> Contract:
        """Apply IBKR-specific symbol resolution and exchange rules."""
        # Example: Map ES to its IBKR equivalent
        ibkr_symbol_map = {
            'ES': 'ES',  # E-mini S&P 500
            'NQ': 'NQ',  # E-mini NASDAQ
            'RTY': 'RTY',  # E-mini Russell 2000
            'YM': 'YM'   # E-mini Dow
        }
        
        underlying = self._extract_underlying_symbol(original_symbol)
        contract.symbol = ibkr_symbol_map.get(underlying, underlying)
        
        # Set appropriate exchange
        if underlying in ['ES', 'NQ']:
            contract.exchange = 'GLOBEX'
        else:
            contract.exchange = 'CME'
            
        return contract

    def _resolve_underlying_index(self, symbol: str) -> str:
        """Resolve underlying index from IBKR symbol."""
        index_map = {
            'ES': 'SPX',      # S&P 500
            'NQ': 'NDX',      # NASDAQ 100
            'RTY': 'RUT',     # Russell 2000
            'YM': 'DJI'       # Dow Jones
        }
        return index_map.get(symbol, symbol)

    def _resolve_contract_size(self, symbol: str) -> int:
        """Resolve contract size from IBKR symbol."""
        size_map = {
            'ES': 50,     # $50 per point
            'NQ': 20,     # $20 per point
            'RTY': 50,    # $50 per point
            'YM': 5       # $5 per point
        }
        return size_map.get(symbol, 1)

    def _normalize_symbol(self, contract: Contract) -> str:
        """Create normalized symbol from IBKR contract."""
        return f"{contract.symbol}{contract.lastTradeDateOrContractMonth[-3:]}"

    def _parse_expiry_date(self, expiry_str: str) -> Optional[date]:
        """Parse expiry date string to date object."""
        try:
            # Handle various IBKR date formats
            if len(expiry_str) == 6:  # YYYYMM
                year = int(expiry_str[:4])
                month = int(expiry_str[4:6])
                return date(year, month, 1)  # Use first day of month
            elif len(expiry_str) == 8:  # YYYYMMDD
                year = int(expiry_str[:4])
                month = int(expiry_str[4:6])
                day = int(expiry_str[6:8])
                return date(year, month, day)
            return None
        except (ValueError, TypeError):
            return None