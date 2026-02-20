"""
IBKR Index Future Repository - Interactive Brokers implementation for Index Futures.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

import os
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.infrastructure.repositories.mappers.finance.financial_assets.index_future_mapper import IndexFutureMapper
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

    def __init__(self, ibkr_client, factory=None, mapper: IndexFutureMapper = None):
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
        self.mapper = mapper or IndexFutureMapper()
    @property
    def entity_class(self):
        """Return the domain entity class for IndexFuture."""
        return self.mapper.entity_class
    @property
    def model_class(self):
        return self.mapper.model_class
    def _create_or_get(self, symbol: str) -> Optional[IndexFuture]:
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
            print(f"Error in IBKR get_or_create for symbol {symbol}: {e}_{os.path.abspath(__file__)}")
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
            contract.tradingClass = contract.symbol
            contract.secType = "FUT"
            contract.exchange = "CME"  
            #contract.lastTradeDateOrContractMonth = self._extract_expiry_from_symbol(symbol)
            
            # Additional IBKR-specific contract setup
            #contract = self._apply_ibkr_symbol_rules(contract, symbol)
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR contract for {symbol}: {e}_{os.path.abspath(__file__)}")
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
        Convert IBKR contract and details to domain entity using intelligent contract selection.
        
        Args:
            contract: IBKR Contract object
            contract_details_list: List of contract details dictionaries from IBKR API
            
        Returns:
            IndexFuture domain entity or None if conversion failed
        """
        try:
            # Select the appropriate contract from multiple available contracts
            contract_details = self._select_optimal_contract(contract_details_list)
            if not contract_details:
                print(f"No suitable contract found from {len(contract_details_list)} available contracts")
                return None
            
            # Apply IBKR-specific business rules and create domain entity
            underlying_index = self._resolve_underlying_index(contract.symbol)
            contract_size = self._resolve_contract_size(contract.symbol)
            tick_size = contract_details.get('min_tick', 0.25)
            
            # Get or create currency and exchange dependencies
            currency = self._get_or_create_currency(contract.currency, f"{contract.currency} Currency")
            exchange = self._get_or_create_exchange(contract.exchange)
            
            return self.entity_class(
                id=None,
                name=f"{self._normalize_symbol(contract)} Index Future",
                symbol=self._normalize_symbol(contract),
                exchange_id=exchange.id if exchange else None,
                currency_id=currency.id if currency else None,
                contract_size=contract_size,
                underlying_index=underlying_index,
                # Additional IBKR-specific fields
                # ibkr_contract_id=getattr(contract, 'conId', None),
                # ibkr_local_symbol=getattr(contract, 'localSymbol', ''),
                # ibkr_trading_class=getattr(contract, 'tradingClass', '')
            )
        except Exception as e:
            print(f"Error converting IBKR contract to domain entity: {e}_{os.path.abspath(__file__)}")
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

    def _select_optimal_contract(self, contract_details_list: List[dict], strategy: str = "front_month") -> Optional[dict]:
        """
        Select the optimal contract from multiple available contracts.
        
        Args:
            contract_details_list: List of contract details from IBKR API
            strategy: Selection strategy ("front_month", "most_liquid", "specific_expiry")
            
        Returns:
            Selected contract details dictionary or None
        """
        if not contract_details_list:
            return None
            
        if len(contract_details_list) == 1:
            return contract_details_list[0]
            
        try:
            if strategy == "front_month":
                return self._select_front_month_contract(contract_details_list)
            elif strategy == "most_liquid":
                return self._select_most_liquid_contract(contract_details_list)
            else:
                # Default to front month
                return self._select_front_month_contract(contract_details_list)
        except Exception as e:
            print(f"Error selecting optimal contract: {e}")
            # Fall back to first contract if selection fails
            return contract_details_list[0]

    def _select_front_month_contract(self, contract_details_list: List[dict]) -> Optional[dict]:
        """
        Select the front month (nearest expiry) contract from the list.
        
        Args:
            contract_details_list: List of contract details from IBKR API
            
        Returns:
            Contract details for front month contract or None
        """
        valid_contracts = []
        
        for contract_dict in contract_details_list:
            local_symbol = contract_dict.get('local_symbol', '')
            if not local_symbol:
                continue
                
            # Parse expiry from local symbol using ContractResolver logic
            expiry = self._parse_expiry_from_local_symbol(local_symbol)
            if expiry:
                valid_contracts.append((expiry, contract_dict))
                print(f"Valid contract found: {local_symbol} -> expiry {expiry}")
            else:
                print(f"Could not parse expiry from local symbol: {local_symbol}")
        
        if not valid_contracts:
            print(f"No valid contracts with parseable expiry dates")
            return None
            
        # Sort by expiry date (earliest first) and return the front month
        front_contract_tuple = min(valid_contracts, key=lambda x: x[0])
        front_expiry, front_contract_dict = front_contract_tuple
        
        print(f"Selected front month contract: {front_contract_dict.get('local_symbol')} (expiry: {front_expiry})")
        return front_contract_dict

    def _select_most_liquid_contract(self, contract_details_list: List[dict]) -> Optional[dict]:
        """
        Select the most liquid contract (placeholder - would need volume data).
        
        Args:
            contract_details_list: List of contract details from IBKR API
            
        Returns:
            Most liquid contract details or front month as fallback
        """
        # For now, fall back to front month selection
        # In a real implementation, you'd need to request market data for volume comparison
        print("Most liquid selection not yet implemented, using front month instead")
        return self._select_front_month_contract(contract_details_list)

    def _parse_expiry_from_local_symbol(self, local_symbol: str) -> str:
        """
        Parse expiry from futures local symbol (adapted from ContractResolver).
        
        Args:
            local_symbol: Local symbol like 'ESZ24', 'ESH25', etc.
            
        Returns:
            Expiry in YYYYMM format or None if parsing failed
        """
        month_codes = {
            "F": "01", "G": "02", "H": "03", "J": "04", "K": "05", "M": "06",
            "N": "07", "Q": "08", "U": "09", "V": "10", "X": "11", "Z": "12"
        }
        
        import re
        
        # Try multiple patterns to support different futures naming conventions
        patterns = [
            # Pattern 1: ESZ24 (2-digit year) - most common for current contracts
            r"^[A-Z]+([A-Z])(\d{2})$",
            # Pattern 2: ESZ4 (1-digit year) - legacy format
            r"^[A-Z]+([A-Z])(\d)$",
            # Pattern 3: More flexible pattern with optional numbers in symbol
            r"^[A-Z0-9]*([A-Z])(\d{1,2})$"
        ]
        
        for pattern in patterns:
            match = re.match(pattern, local_symbol)
            if match:
                month_code, year_str = match.groups()
                
                # Get month number
                month = month_codes.get(month_code)
                if not month:
                    continue  # Try next pattern
                
                # Handle year conversion
                if len(year_str) == 1:
                    # 1-digit year: assume 202X
                    year = f"202{year_str}"
                elif len(year_str) == 2:
                    # 2-digit year: convert to full year
                    year_int = int(year_str)
                    if year_int >= 70:  # 70-99 -> 1970-1999 (shouldn't happen for futures)
                        year = f"19{year_str}"
                    else:  # 00-69 -> 2000-2069
                        year = f"20{year_str}"
                
                expiry = f"{year}{month}"
                return expiry
        
        return None

    def get_optimized_historical_data(self, symbol: str, **kwargs) -> Optional[dict]:
        """
        Get historical data with optimized settings to avoid 'thick data size'.
        
        Args:
            symbol: Index future symbol (e.g., 'ES')
            **kwargs: Additional parameters for customization
            
        Returns:
            Historical data with lightweight configuration
        """
        try:
            # Default lightweight configuration
            config = {
                'duration': kwargs.get('duration', '3 D'),  # 3 days instead of weeks
                'bar_size': kwargs.get('bar_size', '1 hour'),  # 1 hour instead of minutes
                'what_to_show': kwargs.get('what_to_show', 'TRADES'),  # Just trades, not all tick types
                'use_rth': kwargs.get('use_rth', True),  # Regular trading hours only
                'format_date': kwargs.get('format_date', 1)  # Simple date format
            }
            
            print(f"Requesting optimized historical data for {symbol} with config: {config}")
            
            # Get the index future entity first
            entity = self._create_or_get(symbol)
            if not entity:
                return None
                
            # Use the broker's historical data method with optimized settings
            if hasattr(self.ib_broker, 'get_historical_data'):
                # Create a lightweight contract for historical data request
                contract = self._fetch_contract(symbol)
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
            print(f"Error getting optimized historical data for {symbol}: {e}")
            return None

    def set_default_data_config(self, config: dict) -> None:
        """
        Set default configuration for lightweight data operations.
        
        Args:
            config: Configuration dictionary with data preferences
        """
        self._default_data_config = {
            'duration': config.get('duration', '3 D'),
            'bar_size': config.get('bar_size', '1 hour'),
            'what_to_show': config.get('what_to_show', 'TRADES'),
            'use_rth': config.get('use_rth', True),
            'max_contracts_process': config.get('max_contracts_process', 5)  # Limit processing
        }
        print(f"Updated default data config: {self._default_data_config}")

    def get_contract_count_info(self, symbol: str) -> dict:
        """
        Get information about available contracts without processing all of them.
        
        Args:
            symbol: Index future symbol
            
        Returns:
            Dictionary with contract count and basic info
        """
        try:
            contract = self._fetch_contract(symbol)
            if not contract:
                return {'error': 'Could not fetch contract'}
                
            contract_details_list = self._fetch_contract_details(contract)
            if not contract_details_list:
                return {'error': 'No contract details found'}
                
            info = {
                'total_contracts': len(contract_details_list),
                'symbol': symbol,
                'contracts_preview': []
            }
            
            # Add preview of first few contracts to avoid processing all
            for i, contract_dict in enumerate(contract_details_list[:3]):  # Only first 3
                local_symbol = contract_dict.get('local_symbol', 'N/A')
                expiry = self._parse_expiry_from_local_symbol(local_symbol)
                info['contracts_preview'].append({
                    'index': i,
                    'local_symbol': local_symbol,
                    'expiry': expiry,
                    'exchange': contract_dict.get('exchange', 'N/A')
                })
                
            return info
            
        except Exception as e:
            return {'error': f'Failed to get contract info: {e}'}