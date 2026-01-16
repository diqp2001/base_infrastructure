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


class IBKRIndexRepository(IBKRFinancialAssetRepository, IndexPort):
    """
    IBKR implementation of IndexPort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, local_repo: IndexPort):
        """
        Initialize IBKR Index Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            local_repo: Local repository implementing IndexPort for persistence
        """
        self.ibkr = ibkr_client
        self.local_repo = local_repo
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
        Fetch index contract from IBKR API.
        
        Args:
            symbol: Index symbol
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            contract.symbol = symbol.upper()
            contract.secType = "IND"  # Index security type
            contract.currency = "USD"
            
            # Set appropriate exchange for the index
            contract.exchange = self._get_index_exchange(symbol)
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR index contract for {symbol}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[ContractDetails]:
        """
        Fetch index contract details from IBKR API.
        
        Args:
            contract: IBKR Contract object
            
        Returns:
            ContractDetails object or None if not found
        """
        try:
            import time
            import random
            
            # Generate unique request ID
            req_id = self._generate_request_id()
            
            # Clear any existing data for this request
            if hasattr(self.ibkr, 'contract_details') and req_id in self.ibkr.contract_details:
                del self.ibkr.contract_details[req_id]
            
            # Request contract details from IBKR API
            if hasattr(self.ibkr, 'request_contract_details'):
                self.ibkr.request_contract_details(req_id, contract)
            else:
                # Fallback to direct method if available
                self.ibkr.reqContractDetails(req_id, contract)
            
            # Wait for response (with timeout)
            timeout = 10  # 10 seconds timeout
            wait_interval = 0.1
            elapsed = 0
            
            while elapsed < timeout:
                if (hasattr(self.ibkr, 'contract_details') and 
                    req_id in self.ibkr.contract_details and 
                    len(self.ibkr.contract_details[req_id]) > 0):
                    
                    # Get the first contract details result
                    contract_info = self.ibkr.contract_details[req_id][0]
                    
                    # Create ContractDetails object from response
                    contract_details = ContractDetails()
                    contract_details.contract = contract
                    contract_details.marketName = contract_info.get('market_name', 'Index Market')
                    contract_details.longName = contract_info.get('long_name', f"{contract.symbol} Index")
                    contract_details.minTick = contract_info.get('min_tick', 0.01)
                    contract_details.priceMagnifier = contract_info.get('price_magnifier', 1)
                    contract_details.timeZoneId = contract_info.get('time_zone_id', 'EST')
                    contract_details.tradingHours = contract_info.get('trading_hours', '')
                    contract_details.liquidHours = contract_info.get('liquid_hours', '')
                    contract_details.orderTypes = ""  # Indices are not tradeable directly
                    
                    # Store contract ID if available
                    if 'contract_id' in contract_info:
                        contract.conId = contract_info['contract_id']
                    
                    return contract_details
                
                time.sleep(wait_interval)
                elapsed += wait_interval
            
            print(f"Timeout waiting for IBKR contract details for {contract.symbol}")
            return None
            
        except Exception as e:
            print(f"Error fetching IBKR index contract details: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details: ContractDetails) -> Optional[Index]:
        """
        Convert IBKR contract and details to domain entity using real API data.
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object
            
        Returns:
            Index domain entity or None if conversion failed
        """
        try:
            # Use real data from IBKR API response
            symbol = contract.symbol
            name = getattr(contract_details, 'longName', f"{symbol} Index")
            description = f"{name} - {getattr(contract_details, 'marketName', 'Index Market')}"
            
            # Determine index properties intelligently based on symbol and API data
            index_type = self._determine_index_type(symbol)
            base_value = self._determine_base_value(symbol)
            base_date = self._determine_base_date(symbol)
            weighting_method = self._determine_weighting_method(symbol)
            calculation_method = self._determine_calculation_method(symbol)
            
            return Index(
                id=None,  # Let database generate
                symbol=symbol,
                name=name,
                description=description,
                index_type=index_type,
                base_value=base_value,
                base_date=base_date,
                currency=contract.currency,
                weighting_method=weighting_method,
                calculation_method=calculation_method,
                # IBKR-specific fields from real API response
                ibkr_contract_id=getattr(contract, 'conId', None),
                ibkr_local_symbol=getattr(contract, 'localSymbol', ''),
                ibkr_exchange=contract.exchange,
                ibkr_min_tick=Decimal(str(getattr(contract_details, 'minTick', 0.01)))
            )
        except Exception as e:
            print(f"Error converting IBKR index contract to domain entity: {e}")
            return None

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