"""
IBKR Currency Repository - Interactive Brokers implementation for Currencies.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.domain.ports.finance.financial_assets.currency_port import CurrencyPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_repository import BaseIBKRRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_base_repository import FinancialAssetBaseRepository
from src.domain.entities.finance.financial_assets.currency import Currency


class IBKRCurrencyRepository(FinancialAssetBaseRepository, CurrencyPort):
    """
    IBKR implementation of CurrencyPort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, local_repo: CurrencyPort):
        """
        Initialize IBKR Currency Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            local_repo: Local repository implementing CurrencyPort for persistence
        """
        self.ibkr = ibkr_client
        self.local_repo = local_repo

    def get_or_create(self, pair_symbol: str) -> Optional[Currency]:
        """
        Get or create a currency pair by symbol using IBKR API.
        
        Args:
            pair_symbol: The currency pair symbol (e.g., 'EURUSD', 'GBPJPY')
            
        Returns:
            Currency entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            existing = self.local_repo.get_by_symbol(pair_symbol)
            if existing:
                return existing
            
            # 2. Fetch from IBKR API
            contract = self._fetch_contract(pair_symbol)
            if not contract:
                return None
                
            # 3. Get contract details from IBKR
            contract_details = self._fetch_contract_details(contract)
            if not contract_details:
                return None
                
            # 4. Apply IBKR-specific rules and convert to domain entity
            entity = self._contract_to_domain(contract, contract_details, pair_symbol)
            if not entity:
                return None
                
            # 5. Delegate persistence to local repository
            return self.local_repo.add(entity)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for currency pair {pair_symbol}: {e}")
            return None

    def get_by_symbol(self, symbol: str) -> Optional[Currency]:
        """Get currency by symbol (delegates to local repository)."""
        return self.local_repo.get_by_symbol(symbol)

    def get_by_id(self, entity_id: int) -> Optional[Currency]:
        """Get currency by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Currency]:
        """Get all currencies (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Currency) -> Optional[Currency]:
        """Add currency entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Currency) -> Optional[Currency]:
        """Update currency entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete currency entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def _fetch_contract(self, pair_symbol: str) -> Optional[Contract]:
        """
        Fetch currency contract from IBKR API.
        
        Args:
            pair_symbol: Currency pair symbol (e.g., 'EURUSD')
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            # Parse currency pair
            base_currency, quote_currency = self._parse_currency_pair(pair_symbol)
            
            contract = Contract()
            contract.symbol = base_currency
            contract.secType = "CASH"
            contract.exchange = "IDEALPRO"  # IBKR's forex exchange
            contract.currency = quote_currency
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR currency contract for {pair_symbol}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[ContractDetails]:
        """
        Fetch currency contract details from IBKR API.
        
        Args:
            contract: IBKR Contract object
            
        Returns:
            ContractDetails object or None if not found
        """
        try:
            # Mock implementation - in real code use self.ibkr.reqContractDetails()
            contract_details = ContractDetails()
            contract_details.contract = contract
            contract_details.marketName = "Forex Market"
            contract_details.minTick = 0.00001  # Typical forex pip
            contract_details.priceMagnifier = 1
            contract_details.orderTypes = "LMT,MKT,STP,TRAIL"
            contract_details.longName = f"{contract.symbol}/{contract.currency}"
            
            return contract_details
        except Exception as e:
            print(f"Error fetching IBKR currency contract details: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details: ContractDetails, pair_symbol: str) -> Optional[Currency]:
        """
        Convert IBKR contract and details directly to domain entity.
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object
            pair_symbol: Original pair symbol
            
        Returns:
            Currency domain entity or None if conversion failed
        """
        try:
            base_currency, quote_currency = self._parse_currency_pair(pair_symbol)
            
            return Currency(
                id=None,  # Let database generate
                symbol=pair_symbol,
                name=f"{base_currency}/{quote_currency}",
                base_currency=base_currency,
                quote_currency=quote_currency,
                pip_size=Decimal(str(contract_details.minTick)) if hasattr(contract_details, 'minTick') else Decimal('0.00001'),
                # IBKR-specific fields
                ibkr_contract_id=getattr(contract, 'conId', None),
                ibkr_local_symbol=getattr(contract, 'localSymbol', ''),
                ibkr_trading_class=getattr(contract, 'tradingClass', ''),
                ibkr_exchange=contract.exchange
            )
        except Exception as e:
            print(f"Error converting IBKR currency contract to domain entity: {e}")
            return None

    def _parse_currency_pair(self, pair_symbol: str) -> tuple[str, str]:
        """
        Parse currency pair symbol into base and quote currencies.
        
        Args:
            pair_symbol: Currency pair (e.g., 'EURUSD', 'GBPJPY')
            
        Returns:
            Tuple of (base_currency, quote_currency)
        """
        if len(pair_symbol) != 6:
            raise ValueError(f"Invalid currency pair format: {pair_symbol}")
        
        base = pair_symbol[:3].upper()
        quote = pair_symbol[3:].upper()
        
        # Validate currency codes
        valid_currencies = {
            'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD', 
            'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'RUB', 'CNH',
            'HKD', 'SGD', 'ZAR', 'MXN', 'BRL', 'INR', 'KRW', 'TRY'
        }
        
        if base not in valid_currencies or quote not in valid_currencies:
            raise ValueError(f"Invalid currency codes in pair: {base}/{quote}")
        
        return base, quote

    def get_major_pairs(self) -> List[Currency]:
        """Get major currency pairs from IBKR."""
        major_pairs = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'USDCAD', 'AUDUSD', 'NZDUSD'
        ]
        
        currencies = []
        for pair in major_pairs:
            currency = self.get_or_create(pair)
            if currency:
                currencies.append(currency)
        
        return currencies