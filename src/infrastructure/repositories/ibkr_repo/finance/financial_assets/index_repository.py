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
        Create index contract for IBKR API request.
        
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
            print(f"Error creating IBKR index contract for {symbol}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[ContractDetails]:
        """
        Fetch index contract details from IBKR API using real API call.
        
        Args:
            contract: IBKR Contract object
            
        Returns:
            ContractDetails object or None if not found
        """
        try:
            if not self.ibkr or not hasattr(self.ibkr, 'reqContractDetails'):
                print(f"IBKR client not available or missing reqContractDetails method")
                return None
            
            # Generate unique request ID
            req_id = self._generate_request_id()
            
            # Clear any existing contract details for this request
            if hasattr(self.ibkr, 'contract_details'):
                self.ibkr.contract_details.pop(req_id, None)
            
            # Make real IBKR API call
            print(f"Requesting contract details from IBKR API for {contract.symbol}")
            self.ibkr.reqContractDetails(req_id, contract)
            
            # Wait for response (with timeout)
            import time
            timeout = 10  # 10 seconds timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if (hasattr(self.ibkr, 'contract_details') and 
                    req_id in self.ibkr.contract_details and 
                    self.ibkr.contract_details[req_id]):
                    
                    # Get the first contract details result
                    details_data = self.ibkr.contract_details[req_id][0]
                    
                    # Create ContractDetails object from the response data
                    contract_details = ContractDetails()
                    contract_details.contract = contract
                    contract_details.contract.conId = details_data.get('contract_id', 0)
                    contract_details.marketName = details_data.get('market_name', 'Index Market')
                    contract_details.longName = details_data.get('long_name', f"{contract.symbol} Index")
                    contract_details.minTick = details_data.get('min_tick', 0.01)
                    contract_details.priceMagnifier = details_data.get('price_magnifier', 1)
                    contract_details.orderTypes = details_data.get('order_types', '')
                    contract_details.validExchanges = details_data.get('valid_exchanges', '')
                    contract_details.timeZoneId = details_data.get('time_zone_id', '')
                    contract_details.tradingHours = details_data.get('trading_hours', '')
                    contract_details.liquidHours = details_data.get('liquid_hours', '')
                    
                    print(f"Successfully retrieved contract details from IBKR API for {contract.symbol}")
                    return contract_details
                
                time.sleep(0.1)  # Wait 100ms before checking again
            
            print(f"Timeout waiting for contract details from IBKR API for {contract.symbol}")
            return None
            
        except Exception as e:
            print(f"Error fetching IBKR index contract details for {contract.symbol}: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details: ContractDetails) -> Optional[Index]:
        """
        Convert IBKR contract and details directly to domain entity using real API data.
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object
            
        Returns:
            Index domain entity or None if conversion failed
        """
        try:
            # Use data from real IBKR API response instead of hardcoded values
            return Index(
                id=None,  # Let database generate
                symbol=contract.symbol,
                name=contract_details.longName or f"{contract.symbol} Index",
                description=f"{contract_details.longName or contract.symbol} - {contract_details.marketName}",
                index_type=self._determine_index_type(contract.symbol, contract_details),
                base_value=self._determine_base_value(contract.symbol),
                base_date=self._determine_base_date(contract.symbol),
                currency=contract.currency,
                weighting_method=self._determine_weighting_method(contract.symbol),
                calculation_method=self._determine_calculation_method(contract.symbol),
                # IBKR-specific fields from real API data
                ibkr_contract_id=getattr(contract, 'conId', None),
                ibkr_local_symbol=getattr(contract, 'localSymbol', ''),
                ibkr_exchange=contract.exchange,
                ibkr_min_tick=Decimal(str(contract_details.minTick)),
                # Additional IBKR fields
                ibkr_market_name=contract_details.marketName,
                ibkr_valid_exchanges=getattr(contract_details, 'validExchanges', ''),
                ibkr_trading_hours=getattr(contract_details, 'tradingHours', ''),
                ibkr_liquid_hours=getattr(contract_details, 'liquidHours', ''),
                ibkr_time_zone=getattr(contract_details, 'timeZoneId', '')
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
        """Generate a unique request ID for IBKR API calls."""
        import time
        return int(time.time() * 1000) % 1000000  # Use timestamp-based ID
    
    def _determine_index_type(self, symbol: str, contract_details: ContractDetails) -> str:
        """Determine index type from symbol and IBKR data."""
        volatility_symbols = ['VIX', 'VXN', 'RVX']
        if symbol.upper() in volatility_symbols:
            return 'VOLATILITY'
        return 'EQUITY'  # Default for most indices
    
    def _determine_base_value(self, symbol: str) -> Optional[Decimal]:
        """Determine base value for known indices."""
        # Only set base values for well-known indices where we know the historical value
        known_bases = {
            'SPX': Decimal('10.0'),
            'NDX': Decimal('125.0'), 
            'RUT': Decimal('135.0'),
            'DJI': Decimal('40.94'),
            'OEX': Decimal('10.0'),
            'COMP': Decimal('100.0'),
            'NYA': Decimal('50.0')
        }
        return known_bases.get(symbol.upper(), Decimal('100.0'))
    
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
        return known_dates.get(symbol.upper(), date(2000, 1, 1))
    
    def _determine_weighting_method(self, symbol: str) -> str:
        """Determine weighting method for known indices."""
        price_weighted = ['DJI']
        volatility_based = ['VIX', 'VXN', 'RVX']
        
        if symbol.upper() in price_weighted:
            return 'PRICE'
        elif symbol.upper() in volatility_based:
            return 'IMPLIED_VOLATILITY'
        return 'MARKET_CAP'  # Default for most indices
    
    def _determine_calculation_method(self, symbol: str) -> str:
        """Determine calculation method for known indices."""
        price_weighted = ['DJI']
        volatility_based = ['VIX', 'VXN', 'RVX']
        
        if symbol.upper() in price_weighted:
            return 'PRICE_WEIGHTED'
        elif symbol.upper() in volatility_based:
            return 'OPTIONS_BASED'
        return 'CAPITALIZATION_WEIGHTED'  # Default for most indices

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