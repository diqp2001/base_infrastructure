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
        Resolve the front month futures contract (IBKR-safe).
        """

        cache_key = f"FUT_{symbol}_{exchange}_front"

        if self._is_cached(cache_key):
            return self._contract_cache[cache_key]

        try:
            base_contract = Contract()
            base_contract.symbol = symbol
            base_contract.secType = "FUT"
            base_contract.exchange = exchange
            base_contract.currency = "USD"

            self.logger.info(f"Resolving front month future for {symbol} on {exchange}")

            req_id = abs(hash(f"cd_{symbol}_{time.time()}")) % 10000
            self.ib.contract_details.pop(req_id, None)

            self.ib.request_contract_details(req_id, base_contract)

            timeout = 10
            waited = 0.0

            while waited < timeout:
                time.sleep(0.2)
                waited += 0.2
                if req_id in self.ib.contract_details and self.ib.contract_details[req_id]:
                    break

            details_list = self.ib.contract_details.get(req_id, [])

            if not details_list:
                self.logger.error(f"No contract details found for {symbol}")
                return None

            valid_contracts = []

            for d in details_list:
                local_symbol = d.get("local_symbol")
                expiry = self.parse_expiry_from_local_symbol(local_symbol)
                if not expiry:
                    continue
                valid_contracts.append((expiry, d))
                self.logger.debug(f"Found contract: {local_symbol} expiry {expiry}")

            if not valid_contracts:
                self.logger.error(f"No valid expiries found for {symbol}")
                return None

            # Front month = earliest expiry
            front_contract_tuple = min(valid_contracts, key=lambda x: x[0])
            front_expiry, front_contract_dict = front_contract_tuple

            # Build the resolved Contract from dict
            front_contract = Contract()
            front_contract.symbol = front_contract_dict.get("symbol")
            front_contract.secType = "FUT"
            front_contract.exchange = front_contract_dict.get("exchange", "CME")
            front_contract.currency = front_contract_dict.get("currency", "USD")
            front_contract.localSymbol = front_contract_dict.get("local_symbol")
            front_contract.tradingClass = front_contract_dict.get("trading_class")
            front_contract.lastTradeDateOrContractMonth = front_expiry

            # Map contract_id to conId
            front_contract.conId = front_contract_dict.get("contract_id")

            # Optional: multiplier
            if "multiplier" in front_contract_dict:
                front_contract.multiplier = front_contract_dict["multiplier"]

            # Validate conId
            if not front_contract.conId:
                self.logger.error("Resolved front contract has no conId (invalid)")
                return None

            # Cache and log
            self._cache_contract(cache_key, front_contract)
            self.logger.info(
                f"Resolved front month future: {symbol} -> "
                f"{front_contract.localSymbol} "
                f"(exp={front_contract.lastTradeDateOrContractMonth}, conId={front_contract.conId})"
            )

            # Cleanup
            self.ib.contract_details.pop(req_id, None)
            return front_contract

        except Exception as e:
            self.logger.error(f"Error resolving front month future for {symbol}: {e}")
            return None
        
    def parse_expiry_from_local_symbol(self,local_symbol: str) -> str:
        month_codes = {
            "F": "01","G": "02","H": "03","J": "04","K": "05","M": "06",
            "N": "07","Q": "08","U": "09","V": "10","X": "11","Z": "12"
        }
        import re
        match = re.match(r"^[A-Z]+([A-Z])(\d)$", local_symbol)
        if not match:
            return None
        month_code, year_digit = match.groups()
        month = month_codes.get(month_code)
        year = f"202{year_digit}"  # Adjust if year > 2030
        return f"{year}{month}"
    
    def resolve_future_by_expiry(
        self,
        symbol: str,
        expiry_yyyymm: str,
        exchange: str = "GLOBEX") -> Optional[Contract]:

        cache_key = f"FUT_{symbol}_{exchange}_{expiry_yyyymm}"

        if self._is_cached(cache_key):
            return self._contract_cache[cache_key]

        try:
            base_contract = Contract()
            base_contract.symbol = symbol
            base_contract.secType = "FUT"
            base_contract.exchange = exchange
            base_contract.currency = "USD"
            base_contract.lastTradeDateOrContractMonth = expiry_yyyymm

            resolved = self._validate_contract(base_contract)

            if not resolved or not resolved.conId:
                self.logger.error(
                    f"Failed to resolve future {symbol} {expiry_yyyymm}"
                )
                return None

            self._cache_contract(cache_key, resolved)

            self.logger.info(
                f"Resolved future by expiry: {symbol} "
                f"{expiry_yyyymm} (conId={resolved.conId})"
            )

            return resolved

        except Exception as e:
            self.logger.error(
                f"Error resolving future by expiry {symbol} {expiry_yyyymm}: {e}"
            )
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
