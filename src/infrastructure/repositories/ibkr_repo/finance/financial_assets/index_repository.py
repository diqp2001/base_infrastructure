"""
IBKR Index Repository - Interactive Brokers implementation for Indices.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.domain.ports.finance.financial_assets.index.index_port import IndexPort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.domain.entities.finance.financial_assets.index.index import Index
from src.domain.entities.finance.financial_assets.currency import Currency


class IBKRIndexRepository(IBKRFinancialAssetRepository, IndexPort):
    """
    IBKR implementation of IndexPort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client,  factory=None):
        """
        Initialize IBKR Index Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client (InteractiveBrokersBroker instance)
            local_repo: Local repository implementing IndexPort for persistence
            factory: Repository factory for dependency injection (preferred)
            currency_repo: Currency repository for get-or-create currency functionality (legacy)
        """
        self.ib_broker = ibkr_client  # Use ib_broker for consistency with reference implementation
        
        self.factory = factory
        self.local_repo = self.factory.index_local_repo
    @property
    def entity_class(self):
        """Return the SQLAlchemy model class for FactorValue."""
        return Index
    def get_or_create(self, symbol: str) -> Optional[Index]:
        """
        Get or create an index by symbol using IBKR API.
        
        Args:
            symbol: The index symbol (e.g., 'SPX', 'NDX', 'RUT', 'VIX')
            
        Returns:
            Index entity or None if creation/retrieval failed
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
            print(f"Error in IBKR get_or_create for index symbol {symbol}: {e}")
            return None

    def get_by_symbol(self, symbol: str) -> Optional[Index]:
        """Get index by symbol (delegates to local repository)."""
        return self.local_repo.get_by_symbol(symbol)

    def get_by_id(self, entity_id: int) -> Optional[Index]:
        """Get index by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Index]:
        """Get all indices (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Index) -> Optional[Index]:
        """Add index entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Index) -> Optional[Index]:
        """Update index entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete index entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def _fetch_contract(self, symbol: str) -> Optional[Contract]:
        """
        Create index contract using IBKR broker helper method.
        
        Args:
            symbol: Index symbol
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            # Use the broker's helper method to create index contract
            exchange = self._get_index_exchange(symbol)
            contract = self.ib_broker.create_index_contract(
                symbol=symbol.upper(),
                exchange=exchange,
                currency="USD"
            )
            return contract
        except Exception as e:
            print(f"Error creating IBKR index contract for {symbol}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[List[dict]]:
        """
        Fetch index contract details from IBKR API using broker method.
        
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
            print(f"Error fetching IBKR index contract details: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details_list: List[dict]) -> Optional[Index]:
        """
        Convert IBKR contract and details to domain entity using real API data.
        
        Args:
            contract: IBKR Contract object
            contract_details_list: List of contract details dictionaries from IBKR API
            
        Returns:
            Index domain entity or None if conversion failed
        """
        try:
            # Use the first contract details result
            contract_details = contract_details_list[0] if contract_details_list else {}
            
            # Extract data from IBKR API response
            symbol = contract.symbol
            name = contract_details.get('long_name', f"{symbol} Index")
            
            # Get or create USD currency for indices (most indices are USD-denominated)
            usd_currency = self._get_or_create_currency("USD", "US Dollar")
            
            return Index(
                id=None,  # Let database generate
                name=name,
                symbol=symbol,
                currency=usd_currency,
            )
        except Exception as e:
            print(f"Error converting IBKR index contract to domain entity: {e}")
            return None

    def _get_or_create_currency(self, iso_code: str, name: str) -> Currency:
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
            
            
                    
            
            
        except Exception as e:
            print(f"Error getting or creating currency {iso_code}: {e}")
            

    def _get_index_exchange(self, symbol: str) -> str:
        """Get appropriate exchange for index symbol."""
        exchange_map = {
            'SPX': 'CBOE',    # S&P 500
            'NDX': 'NASDAQ',  # NASDAQ 100
            'RUT': 'CBOE',    # Russell 2000
            'DJI': 'NYSE',    # Dow Jones Industrial Average
            'VIX': 'CBOE',    # VIX Volatility Index
            'OEX': 'CBOE',    # S&P 100
            'COMP': 'NASDAQ', # NASDAQ Composite
            'NYA': 'NYSE',    # NYSE Composite
        }
        return exchange_map.get(symbol.upper(), 'CBOE')

    def _generate_request_id(self) -> int:
        """Generate unique request ID for IBKR API calls."""
        import random
        return random.randint(1000, 99999)

    def _determine_index_type(self, symbol: str) -> str:
        """Determine index type based on symbol pattern."""
        volatility_symbols = {'VIX', 'VXN', 'RVX', 'VXD'}
        if symbol.upper() in volatility_symbols:
            return 'VOLATILITY'
        
        commodity_symbols = {'GC', 'SI', 'CL', 'NG'}
        if symbol.upper() in commodity_symbols:
            return 'COMMODITY'
            
        return 'EQUITY'  # Default for most indices

    def _determine_base_value(self, symbol: str) -> Optional[Decimal]:
        """Determine base value for known indices, None for unknown."""
        known_values = {
            'SPX': Decimal('10.0'),
            'OEX': Decimal('10.0'),
            'NDX': Decimal('125.0'),
            'RUT': Decimal('135.0'),
            'DJI': Decimal('40.94'),
            'COMP': Decimal('100.0'),
            'NYA': Decimal('50.0'),
            'VIX': None  # VIX doesn't have a traditional base value
        }
        return known_values.get(symbol.upper(), Decimal('100.0'))

    def _determine_base_date(self, symbol: str) -> Optional[date]:
        """Determine base date for known indices."""
        known_dates = {
            'SPX': date(1957, 3, 4),
            'NDX': date(1985, 2, 1),
            'RUT': date(1986, 12, 31),
            'DJI': date(1896, 5, 26),
            'VIX': date(1993, 1, 1),
            'OEX': date(1983, 1, 3),
            'COMP': date(1971, 2, 5),
            'NYA': date(1966, 1, 3)
        }
        return known_dates.get(symbol.upper())

    def _determine_weighting_method(self, symbol: str) -> str:
        """Determine weighting method based on index characteristics."""
        if symbol.upper() == 'DJI':
            return 'PRICE'
        elif symbol.upper() in {'VIX', 'VXN', 'RVX'}:
            return 'IMPLIED_VOLATILITY'
        else:
            return 'MARKET_CAP'  # Default for most equity indices

    def _determine_calculation_method(self, symbol: str) -> str:
        """Determine calculation method based on index type."""
        if symbol.upper() == 'DJI':
            return 'PRICE_WEIGHTED'
        elif symbol.upper() in {'VIX', 'VXN', 'RVX'}:
            return 'OPTIONS_BASED'
        else:
            return 'CAPITALIZATION_WEIGHTED'  # Default for most equity indices

    def get_major_indices(self) -> List[Index]:
        """Get major market indices from IBKR."""
        major_symbols = ['SPX', 'NDX', 'RUT', 'DJI', 'VIX', 'OEX']
        
        indices = []
        for symbol in major_symbols:
            index = self.get_or_create(symbol)
            if index:
                indices.append(index)
        
        return indices

    def get_equity_indices(self) -> List[Index]:
        """Get equity-based indices."""
        equity_symbols = ['SPX', 'NDX', 'RUT', 'DJI', 'OEX', 'COMP', 'NYA']
        
        indices = []
        for symbol in equity_symbols:
            index = self.get_or_create(symbol)
            if index:
                indices.append(index)
        
        return indices

    def get_volatility_indices(self) -> List[Index]:
        """Get volatility indices."""
        volatility_symbols = ['VIX', 'VXN', 'RVX']
        
        indices = []
        for symbol in volatility_symbols:
            index = self.get_or_create(symbol)
            if index:
                indices.append(index)
        
        return indices