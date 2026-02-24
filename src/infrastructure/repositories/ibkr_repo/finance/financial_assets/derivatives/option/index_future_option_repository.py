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

    def _create_or_get(self, symbol: str, strike_price: float = None, expiry: str = None, option_type: str = None) -> Optional[IndexFutureOption]:
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
            # 1. Check local repository first
            existing = self.local_repo.get_by_symbol_and_strike(symbol, strike_price)
            if existing:
                return existing
            
            # 2. Fetch from IBKR API
            contract = self._fetch_option_contract(symbol, strike_price, expiry, option_type)
            if not contract:
                return None
                
            # 3. Get contract details from IBKR
            contract_details_list = self._fetch_contract_details(contract)
            if not contract_details_list:
                return None
            contract_detail = self.get_contract_by_local_symbol(contract_details_list, symbol)
            
            # 4. Apply IBKR-specific rules and convert to domain entity
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

    def _fetch_option_contract(self, symbol: str, strike_price: float, expiry: str, option_type: str) -> Optional[Contract]:
        """
        Fetch option contract from IBKR API.
        
        Args:
            symbol: Option symbol (e.g., 'ES', 'NQ')
            strike_price: Strike price
            expiry: Expiry date (YYYYMMDD format)
            option_type: 'C' for call, 'P' for put
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            contract.symbol = symbol
            contract.secType = "FOP"  # Future Option
            contract.exchange = "CME"
            contract.currency = "USD"
            contract.strike = strike_price
            contract.lastTradeDateOrContractMonth = expiry
            contract.right = option_type  # 'C' or 'P'
            contract.includeExpired = True
            
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