"""
Contract Resolution Layer for Interactive Brokers API

This module provides a comprehensive contract resolution system that ensures
all IB requests use properly resolved contracts, preventing the systematic
errors that occur when using ad-hoc contract construction.

Fix Issue #6: Enforce Contract Resolution Layer Architecture
"""

from typing import Optional, List, Dict, Any
import time
import logging
from datetime import datetime
from ibapi.contract import Contract

from . import IBTWSClient


class ContractResolver:
    """
    Canonical contract resolver for Interactive Brokers API.
    
    This class ensures that all market data and historical data requests
    use properly resolved contracts instead of ad-hoc constructions,
    preventing common IB API errors.
    """
    
    def __init__(self, ib_client: IBTWSClient):
        """
        Initialize the contract resolver.
        
        Args:
            ib_client: Connected IBTWSClient instance
        """
        self.ib = ib_client
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Contract cache to avoid redundant lookups
        self._contract_cache: Dict[str, Contract] = {}
        self._cache_timeout = 3600  # 1 hour cache
        self._cache_timestamps: Dict[str, float] = {}
    
    def resolve_stock(self, symbol: str, exchange: str = "SMART", primary_exchange: str = "") -> Optional[Contract]:
        """
        Resolve a stock contract with proper exchange information.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            exchange: Exchange to route through (default: "SMART")
            primary_exchange: Primary exchange for the security
            
        Returns:
            Resolved Contract object or None if resolution failed
        """
        cache_key = f"STK_{symbol}_{exchange}_{primary_exchange}"
        
        # Check cache first
        if self._is_cached(cache_key):
            return self._contract_cache[cache_key]
        
        try:
            # Create base contract
            contract = Contract()
            contract.symbol = symbol
            contract.secType = "STK"
            contract.exchange = exchange
            contract.currency = "USD"
            
            # Set primary exchange for ETFs and known securities
            if symbol.upper() in ['SPY', 'QQQ', 'IWM', 'DIA', 'XLF', 'GLD', 'TLT']:
                contract.primaryExchange = primary_exchange or "ARCA"
            elif primary_exchange:
                contract.primaryExchange = primary_exchange
            
            # Validate contract with IB
            resolved_contract = self._validate_contract(contract)
            if resolved_contract:
                self._cache_contract(cache_key, resolved_contract)
                self.logger.info(f"Resolved stock contract: {symbol} ({exchange})")
                return resolved_contract
            else:
                self.logger.error(f"Failed to resolve stock contract: {symbol}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error resolving stock contract for {symbol}: {e}")
            return None
    
    def resolve_front_future(self, symbol: str, exchange: str = "CME") -> Optional[Contract]:
        """
        Resolve the front month futures contract.
        
        This is the MANDATORY fix for Issues #3 and #5.
        Futures cannot be requested generically - you MUST resolve 
        a concrete contract first.
        
        Args:
            symbol: Futures symbol (e.g., "ES", "NQ", "YM") 
            exchange: Futures exchange (e.g., "CME", "CBOT", "NYMEX")
            
        Returns:
            Resolved front month Contract object or None if resolution failed
        """
        cache_key = f"FUT_{symbol}_{exchange}_front"
        
        # Check cache first
        if self._is_cached(cache_key):
            return self._contract_cache[cache_key]
        
        try:
            # Create base contract for contract details lookup
            base_contract = Contract()
            base_contract.symbol = symbol
            base_contract.secType = "FUT"
            base_contract.exchange = exchange
            base_contract.currency = "USD"
            
            self.logger.info(f"Resolving front month future for {symbol} on {exchange}")
            
            # Get all available contract months
            req_id = abs(hash(f"cd_{symbol}_{time.time()}")) % 10000
            
            # Clear any previous results
            self.ib.contract_details.pop(req_id, None)
            
            # Request contract details
            self.ib.request_contract_details(req_id, base_contract)
            
            # Wait for contract details with timeout
            timeout = 10
            wait_interval = 0.2
            total_waited = 0
            
            while total_waited < timeout:
                time.sleep(wait_interval)
                total_waited += wait_interval
                
                if req_id in self.ib.contract_details:
                    contracts = self.ib.contract_details[req_id]
                    if contracts:  # We have contract details
                        break
            
            # Get the resolved contracts
            contract_details_list = self.ib.contract_details.get(req_id, [])
            
            if not contract_details_list:
                self.logger.error(f"No contract details found for futures {symbol}")
                return None
            
            # Find the front month contract (earliest expiry that hasn't expired)
            today = datetime.now().strftime("%Y%m%d")
            
            # Extract contract objects and filter active contracts
            valid_contracts = []
            for details in contract_details_list:
                # Access the contract from details (contract_details contains metadata)
                if hasattr(details, 'contract'):
                    contract = details['contract'] if isinstance(details, dict) else details
                    # Handle both dict and object formats
                    if isinstance(contract, dict):
                        expiry = contract.get('lastTradeDateOrContractMonth', '')
                        local_symbol = contract.get('local_symbol', '')
                    else:
                        expiry = getattr(contract, 'lastTradeDateOrContractMonth', '')
                        local_symbol = getattr(contract, 'local_symbol', '')
                    
                    if expiry >= today:  # Contract hasn't expired
                        valid_contracts.append((expiry, contract))
            
            if not valid_contracts:
                self.logger.error(f"No active futures contracts found for {symbol}")
                return None
            
            # Sort by expiry and get the front month
            valid_contracts.sort(key=lambda x: x[0])
            front_month_expiry, front_contract_data = valid_contracts[0]
            
            # Create the resolved contract
            resolved_contract = Contract()
            resolved_contract.symbol = symbol
            resolved_contract.secType = "FUT"
            resolved_contract.exchange = exchange
            resolved_contract.currency = "USD"
            
            # Set the critical fields that make futures requests work
            if isinstance(front_contract_data, dict):
                resolved_contract.lastTradeDateOrContractMonth = front_contract_data.get('local_symbol', front_month_expiry)
                resolved_contract.localSymbol = front_contract_data.get('local_symbol', '')
            else:
                resolved_contract.lastTradeDateOrContractMonth = front_month_expiry
                resolved_contract.localSymbol = getattr(front_contract_data, 'local_symbol', '')
            
            # Cache and return the resolved contract
            self._cache_contract(cache_key, resolved_contract)
            self.logger.info(f"Resolved front month future: {symbol} -> {resolved_contract.localSymbol} (exp: {front_month_expiry})")
            
            # Cleanup
            self.ib.contract_details.pop(req_id, None)
            
            return resolved_contract
            
        except Exception as e:
            self.logger.error(f"Error resolving front month future for {symbol}: {e}")
            return None
    
    def resolve_future_by_expiry(self, symbol: str, expiry_yyyymm: str, exchange: str = "CME") -> Optional[Contract]:
        """
        Resolve a specific futures contract by expiry month.
        
        Args:
            symbol: Futures symbol (e.g., "ES")
            expiry_yyyymm: Expiry in YYYYMM format (e.g., "202412")
            exchange: Futures exchange
            
        Returns:
            Resolved Contract object or None if resolution failed
        """
        cache_key = f"FUT_{symbol}_{exchange}_{expiry_yyyymm}"
        
        # Check cache first
        if self._is_cached(cache_key):
            return self._contract_cache[cache_key]
        
        try:
            # Use same approach as front month but filter for specific expiry
            base_contract = Contract()
            base_contract.symbol = symbol
            base_contract.secType = "FUT"
            base_contract.exchange = exchange
            base_contract.lastTradeDateOrContractMonth = expiry_yyyymm
            base_contract.currency = "USD"
            
            # Validate the specific contract
            resolved_contract = self._validate_contract(base_contract)
            if resolved_contract:
                self._cache_contract(cache_key, resolved_contract)
                self.logger.info(f"Resolved future by expiry: {symbol} {expiry_yyyymm}")
                return resolved_contract
            else:
                self.logger.error(f"Failed to resolve future: {symbol} {expiry_yyyymm}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error resolving future by expiry {symbol} {expiry_yyyymm}: {e}")
            return None
    
    def _validate_contract(self, contract: Contract) -> Optional[Contract]:
        """
        Validate a contract with Interactive Brokers to ensure it's tradeable.
        
        Args:
            contract: Contract to validate
            
        Returns:
            Validated contract or None if validation failed
        """
        try:
            req_id = abs(hash(f"validate_{contract.symbol}_{time.time()}")) % 10000
            
            # Request contract details to validate
            self.ib.request_contract_details(req_id, contract)
            
            # Wait for response
            timeout = 5
            wait_interval = 0.1
            total_waited = 0
            
            while total_waited < timeout:
                time.sleep(wait_interval)
                total_waited += wait_interval
                
                if req_id in self.ib.contract_details:
                    details = self.ib.contract_details[req_id]
                    if details:  # Validation successful
                        # Clean up and return the original contract (now validated)
                        self.ib.contract_details.pop(req_id, None)
                        return contract
            
            # Validation failed
            self.ib.contract_details.pop(req_id, None)
            return None
            
        except Exception as e:
            self.logger.error(f"Contract validation failed: {e}")
            return None
    
    def _is_cached(self, cache_key: str) -> bool:
        """Check if a contract is cached and not expired."""
        if cache_key not in self._contract_cache:
            return False
            
        # Check if cache entry has expired
        cache_time = self._cache_timestamps.get(cache_key, 0)
        if time.time() - cache_time > self._cache_timeout:
            # Remove expired entry
            self._contract_cache.pop(cache_key, None)
            self._cache_timestamps.pop(cache_key, None)
            return False
            
        return True
    
    def _cache_contract(self, cache_key: str, contract: Contract) -> None:
        """Cache a resolved contract."""
        self._contract_cache[cache_key] = contract
        self._cache_timestamps[cache_key] = time.time()
    
    def clear_cache(self) -> None:
        """Clear the contract cache."""
        self._contract_cache.clear()
        self._cache_timestamps.clear()
        self.logger.info("Contract cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get contract cache statistics."""
        return {
            'cached_contracts': len(self._contract_cache),
            'cache_keys': list(self._contract_cache.keys()),
            'cache_timeout_seconds': self._cache_timeout
        }
