"""
IBKR Security Repository - Interactive Brokers implementation for Securities.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.domain.ports.finance.financial_assets.security_port import SecurityPort
from src.domain.entities.finance.financial_assets.security import Security
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository

class IBKRSecurityRepository(IBKRFinancialAssetRepository, SecurityPort):
    """
    IBKR implementation of SecurityPort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, local_repo: SecurityPort, factory=None):
        """
        Initialize IBKR Security Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client (InteractiveBrokersBroker instance)
            local_repo: Local repository implementing SecurityPort for persistence
            factory: Repository factory for dependency injection (optional)
        """
        self.ib_broker = ibkr_client  # Use ib_broker for consistency with reference implementation
        self.local_repo = local_repo
        self.factory = factory
    @property
    def entity_class(self):
        """Return the domain entity class for Security."""
        return Security
    def get_or_create(self, symbol: str) -> Optional[Security]:
        """
        Get or create a security by symbol using IBKR API.
        
        Args:
            symbol: The security symbol
            
        Returns:
            Security entity or None if creation/retrieval failed
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
            print(f"Error in IBKR get_or_create for security symbol {symbol}: {e}")
            return None

    def get_by_symbol(self, symbol: str) -> Optional[Security]:
        """Get security by symbol (delegates to local repository)."""
        return self.local_repo.get_by_symbol(symbol)

    def get_by_id(self, entity_id: int) -> Optional[Security]:
        """Get security by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Security]:
        """Get all securities (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Security) -> Optional[Security]:
        """Add security entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Security) -> Optional[Security]:
        """Update security entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete security entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def _fetch_contract(self, symbol: str) -> Optional[Contract]:
        """Fetch security contract from IBKR API (auto-detect security type)."""
        try:
            # Try different security types
            for sec_type in ['STK', 'BOND', 'FUT', 'OPT', 'CASH', 'IND']:
                contract = Contract()
                contract.symbol = symbol.upper()
                contract.secType = sec_type
                contract.exchange = "SMART"
                contract.currency = "USD"
                
                # If this would be a real implementation, we'd test each contract
                # For now, default to STK for simplicity
                if sec_type == 'STK':
                    return contract
            
            return None
        except Exception as e:
            print(f"Error fetching IBKR security contract for {symbol}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[List[dict]]:
        """Fetch security contract details from IBKR API using broker method.
        
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
            print(f"Error fetching IBKR security contract details: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details_list: List[dict]) -> Optional[Security]:
        """Convert IBKR contract and details to domain entity using real API data.
        
        Args:
            contract: IBKR Contract object
            contract_details_list: List of contract details dictionaries from IBKR API
            
        Returns:
            Security domain entity or None if conversion failed
        """
        try:
            # Use the first contract details result
            contract_details = contract_details_list[0] if contract_details_list else {}
            
            return Security(
                id=None,
                symbol=contract.symbol,
                name=contract_details.get('long_name', f"{contract.symbol} Security"),
                security_type=contract.secType,
                exchange=contract.exchange,
                currency=contract.currency,
                # IBKR-specific fields
                ibkr_contract_id=getattr(contract, 'conId', None),
                ibkr_local_symbol=getattr(contract, 'localSymbol', ''),
                ibkr_sec_type=contract.secType,
                ibkr_exchange=contract.exchange
            )
        except Exception as e:
            print(f"Error converting IBKR security contract to domain entity: {e}")
            return None