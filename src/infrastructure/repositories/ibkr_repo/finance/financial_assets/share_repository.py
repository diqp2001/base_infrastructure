"""
IBKR Share Repository - Interactive Brokers implementation for Shares.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.domain.ports.finance.financial_assets.share.share_port import SharePort
from src.domain.entities.finance.financial_assets.share.share import Share


class IBKRShareRepository(IBKRFinancialAssetRepository, SharePort):
    """
    IBKR implementation of SharePort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, local_repo: SharePort, factory=None):
        """
        Initialize IBKR Share Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client (InteractiveBrokersBroker instance)
            local_repo: Local repository implementing SharePort for persistence
            factory: Repository factory for dependency injection (optional)
        """
        self.ib_broker = ibkr_client  # Use ib_broker for consistency with reference implementation
        self.local_repo = local_repo
        self.factory = factory
    @property
    def entity_class(self):
        """Return the domain entity class for Share."""
        return Share

    def get_or_create(self, symbol: str) -> Optional[Share]:
        """
        Get or create a share by symbol using IBKR API.
        
        Args:
            symbol: The share symbol/ticker
            
        Returns:
            Share entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            existing = self.local_repo.get_by_ticker(symbol)
            if existing:
                return existing[0] if isinstance(existing, list) else existing
            
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
            print(f"Error in IBKR get_or_create for share symbol {symbol}: {e}")
            return None

    def get_by_ticker(self, ticker: str) -> List[Share]:
        """Get share by ticker (delegates to local repository)."""
        return self.local_repo.get_by_ticker(ticker)

    def get_by_id(self, entity_id: int) -> Optional[Share]:
        """Get share by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Share]:
        """Get all shares (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Share) -> Optional[Share]:
        """Add share entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Share) -> Optional[Share]:
        """Update share entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete share entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def _fetch_contract(self, symbol: str) -> Optional[Contract]:
        """
        Fetch share contract from IBKR API.
        
        Args:
            symbol: Share ticker symbol
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            contract.symbol = symbol.upper()
            contract.secType = "STK"  # Stock/Share
            contract.exchange = "SMART"
            contract.currency = "USD"
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR share contract for {symbol}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[List[dict]]:
        """
        Fetch share contract details from IBKR API using broker method.
        
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
            print(f"Error fetching IBKR share contract details: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details_list: List[dict]) -> Optional[Share]:
        """
        Convert IBKR contract and details to domain entity using real API data.
        
        Args:
            contract: IBKR Contract object
            contract_details_list: List of contract details dictionaries from IBKR API
            
        Returns:
            Share domain entity or None if conversion failed
        """
        try:
            # Use the first contract details result
            contract_details = contract_details_list[0] if contract_details_list else {}
            
            return Share(
                id=None,  # Let database generate
                ticker=contract.symbol,
                exchange_id=self._resolve_exchange_id(contract.exchange),
                company_id=self._resolve_company_id(contract.symbol),
                start_date=None,
                end_date=None,
                # IBKR-specific fields
                ibkr_contract_id=getattr(contract, 'conId', None),
                ibkr_local_symbol=getattr(contract, 'localSymbol', ''),
                ibkr_trading_class=getattr(contract, 'tradingClass', ''),
                ibkr_primary_exchange=getattr(contract, 'primaryExchange', '')
            )
        except Exception as e:
            print(f"Error converting IBKR share contract to domain entity: {e}")
            return None

    def _resolve_exchange_id(self, ibkr_exchange: str) -> int:
        """Resolve exchange ID from IBKR exchange code."""
        exchange_map = {
            'SMART': 1,
            'NASDAQ': 2,
            'NYSE': 3,
            'ARCA': 4,
        }
        return exchange_map.get(ibkr_exchange, 1)

    def _resolve_company_id(self, symbol: str) -> int:
        """Resolve company ID for the share symbol."""
        # This would typically involve looking up or creating company entities
        # For now, return a default mapping
        return 1  # Default company ID