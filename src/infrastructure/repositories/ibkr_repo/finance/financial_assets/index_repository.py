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
from src.infrastructure.repositories.ibkr_repo.base_ibkr_repository import BaseIBKRRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_base_repository import FinancialAssetBaseRepository
from src.domain.entities.finance.financial_assets.index.index import Index


class IBKRIndexRepository(FinancialAssetBaseRepository, IndexPort):
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
            # Mock implementation - in real code use self.ibkr.reqContractDetails()
            contract_details = ContractDetails()
            contract_details.contract = contract
            contract_details.marketName = "Index Market"
            
            index_info = self._get_index_info(contract.symbol)
            contract_details.longName = index_info['name']
            contract_details.minTick = index_info['min_tick']
            contract_details.priceMagnifier = 1
            contract_details.orderTypes = ""  # Indices are not tradeable directly
            
            return contract_details
        except Exception as e:
            print(f"Error fetching IBKR index contract details: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details: ContractDetails) -> Optional[Index]:
        """
        Convert IBKR contract and details directly to domain entity.
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object
            
        Returns:
            Index domain entity or None if conversion failed
        """
        try:
            index_info = self._get_index_info(contract.symbol)
            
            return Index(
                id=None,  # Let database generate
                symbol=contract.symbol,
                name=index_info['name'],
                description=index_info['description'],
                index_type=index_info['type'],
                base_value=index_info['base_value'],
                base_date=index_info['base_date'],
                currency=contract.currency,
                weighting_method=index_info['weighting_method'],
                calculation_method=index_info['calculation_method'],
                # IBKR-specific fields
                ibkr_contract_id=getattr(contract, 'conId', None),
                ibkr_local_symbol=getattr(contract, 'localSymbol', ''),
                ibkr_exchange=contract.exchange,
                ibkr_min_tick=Decimal(str(contract_details.minTick))
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

    def _get_index_info(self, symbol: str) -> dict:
        """Get index information for IBKR symbols."""
        index_data = {
            'SPX': {
                'name': 'S&P 500 Index',
                'description': 'Large-cap US equity index of 500 companies',
                'type': 'EQUITY',
                'base_value': Decimal('10.0'),
                'base_date': date(1957, 3, 4),
                'weighting_method': 'MARKET_CAP',
                'calculation_method': 'CAPITALIZATION_WEIGHTED',
                'min_tick': 0.01
            },
            'NDX': {
                'name': 'NASDAQ-100 Index',
                'description': 'Technology-heavy index of 100 largest NASDAQ companies',
                'type': 'EQUITY',
                'base_value': Decimal('125.0'),
                'base_date': date(1985, 2, 1),
                'weighting_method': 'MARKET_CAP',
                'calculation_method': 'CAPITALIZATION_WEIGHTED',
                'min_tick': 0.01
            },
            'RUT': {
                'name': 'Russell 2000 Index',
                'description': 'Small-cap US equity index',
                'type': 'EQUITY',
                'base_value': Decimal('135.0'),
                'base_date': date(1986, 12, 31),
                'weighting_method': 'MARKET_CAP',
                'calculation_method': 'CAPITALIZATION_WEIGHTED',
                'min_tick': 0.01
            },
            'DJI': {
                'name': 'Dow Jones Industrial Average',
                'description': 'Price-weighted index of 30 large US companies',
                'type': 'EQUITY',
                'base_value': Decimal('40.94'),
                'base_date': date(1896, 5, 26),
                'weighting_method': 'PRICE',
                'calculation_method': 'PRICE_WEIGHTED',
                'min_tick': 0.01
            },
            'VIX': {
                'name': 'CBOE Volatility Index',
                'description': 'Volatility index based on S&P 500 options',
                'type': 'VOLATILITY',
                'base_value': None,
                'base_date': date(1993, 1, 1),
                'weighting_method': 'IMPLIED_VOLATILITY',
                'calculation_method': 'OPTIONS_BASED',
                'min_tick': 0.01
            },
            'OEX': {
                'name': 'S&P 100 Index',
                'description': 'Large-cap US equity index of 100 companies',
                'type': 'EQUITY',
                'base_value': Decimal('10.0'),
                'base_date': date(1983, 1, 3),
                'weighting_method': 'MARKET_CAP',
                'calculation_method': 'CAPITALIZATION_WEIGHTED',
                'min_tick': 0.01
            },
            'COMP': {
                'name': 'NASDAQ Composite Index',
                'description': 'All stocks listed on NASDAQ',
                'type': 'EQUITY',
                'base_value': Decimal('100.0'),
                'base_date': date(1971, 2, 5),
                'weighting_method': 'MARKET_CAP',
                'calculation_method': 'CAPITALIZATION_WEIGHTED',
                'min_tick': 0.01
            },
            'NYA': {
                'name': 'NYSE Composite Index',
                'description': 'All common stocks listed on NYSE',
                'type': 'EQUITY',
                'base_value': Decimal('50.0'),
                'base_date': date(1966, 1, 3),
                'weighting_method': 'MARKET_CAP',
                'calculation_method': 'CAPITALIZATION_WEIGHTED',
                'min_tick': 0.01
            }
        }
        
        return index_data.get(symbol, {
            'name': f'{symbol} Index',
            'description': 'Unknown index',
            'type': 'EQUITY',
            'base_value': Decimal('100.0'),
            'base_date': date(2000, 1, 1),
            'weighting_method': 'MARKET_CAP',
            'calculation_method': 'CAPITALIZATION_WEIGHTED',
            'min_tick': 0.01
        })

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