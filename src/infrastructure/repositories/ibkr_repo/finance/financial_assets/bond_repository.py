"""
IBKR Bond Repository - Interactive Brokers implementation for Bonds.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.domain.ports.finance.financial_assets.bond_port import BondPort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.domain.entities.finance.financial_assets.bond import Bond


class IBKRBondRepository(IBKRFinancialAssetRepository, BondPort):
    """
    IBKR implementation of BondPort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, local_repo: BondPort, factory=None):
        """
        Initialize IBKR Bond Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client (InteractiveBrokersBroker instance)
            local_repo: Local repository implementing BondPort for persistence
            factory: Repository factory for dependency injection (optional)
        """
        self.ib_broker = ibkr_client  # Use ib_broker for consistency with reference implementation
        self.local_repo = local_repo
        self.factory = factory

    @property
    def entity_class(self):
        """Return the domain entity class for Bond."""
        return Bond

    def get_or_create(self, symbol: str) -> Optional[Bond]:
        """
        Get or create a bond by symbol using IBKR API.
        
        Args:
            symbol: The bond identifier (e.g., CUSIP, ISIN)
            
        Returns:
            Bond entity or None if creation/retrieval failed
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
            print(f"Error in IBKR get_or_create for bond symbol {symbol}: {e}")
            return None

    def get_by_symbol(self, symbol: str) -> Optional[Bond]:
        """Get bond by symbol (delegates to local repository)."""
        return self.local_repo.get_by_symbol(symbol)

    def get_by_id(self, entity_id: int) -> Optional[Bond]:
        """Get bond by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Bond]:
        """Get all bonds (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Bond) -> Optional[Bond]:
        """Add bond entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Bond) -> Optional[Bond]:
        """Update bond entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete bond entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def _fetch_contract(self, symbol: str) -> Optional[Contract]:
        """
        Fetch bond contract from IBKR API.
        
        Args:
            symbol: Bond identifier (CUSIP, ISIN, etc.)
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            contract.secType = "BOND"
            contract.exchange = "SMART"
            contract.currency = "USD"
            
            # Try different identifier types
            if len(symbol) == 12 and symbol.isalnum():  # ISIN format
                contract.secIdType = "ISIN"
                contract.secId = symbol
            elif len(symbol) == 9:  # CUSIP format
                contract.secIdType = "CUSIP" 
                contract.secId = symbol
            else:
                # Fallback to symbol
                contract.symbol = symbol
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR bond contract for {symbol}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[List[dict]]:
        """
        Fetch bond contract details from IBKR API using broker method.
        
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
            print(f"Error fetching IBKR bond contract details: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details_list: List[dict]) -> Optional[Bond]:
        """
        Convert IBKR contract and details to domain entity using real API data.
        
        Args:
            contract: IBKR Contract object
            contract_details_list: List of contract details dictionaries from IBKR API
            
        Returns:
            Bond domain entity or None if conversion failed
        """
        try:
            # Use the first contract details result
            contract_details = contract_details_list[0] if contract_details_list else {}
            
            return Bond(
                id=None,  # Let database generate
                symbol=getattr(contract, 'symbol', '') or getattr(contract, 'secId', ''),
                name=contract_details.get('long_name', 'Unknown Bond'),
                issuer=self._extract_issuer_from_name(contract_details.get('long_name', '')),
                face_value=Decimal('1000.00'),  # Typical bond face value
                coupon_rate=Decimal(str(contract_details.get('coupon', 0))),
                maturity_date=self._parse_maturity_date(contract_details.get('maturity', None)),
                currency=contract.currency,
                rating=None,  # Would need separate data source
                bond_type=self._determine_bond_type(contract_details),
                callable=contract_details.get('callable', False),
                # IBKR-specific fields
                ibkr_contract_id=getattr(contract, 'conId', None),
                ibkr_cusip=getattr(contract, 'secId', '') if getattr(contract, 'secIdType', '') == 'CUSIP' else None,
                ibkr_isin=getattr(contract, 'secId', '') if getattr(contract, 'secIdType', '') == 'ISIN' else None
            )
        except Exception as e:
            print(f"Error converting IBKR bond contract to domain entity: {e}")
            return None

    def _extract_issuer_from_name(self, long_name: str) -> str:
        """Extract issuer name from bond's long name."""
        if not long_name:
            return "Unknown Issuer"
        # Simple extraction - in real implementation, use more sophisticated parsing
        return long_name.split()[0] if long_name else "Unknown Issuer"

    def _determine_bond_type(self, contract_details: dict) -> str:
        """Determine bond type from contract details."""
        long_name = contract_details.get('long_name', '').upper()
        
        if 'TREASURY' in long_name or 'T-BILL' in long_name:
            return 'GOVERNMENT'
        elif 'MUNICIPAL' in long_name or 'MUNI' in long_name:
            return 'MUNICIPAL'
        elif 'CORPORATE' in long_name:
            return 'CORPORATE'
        else:
            return 'OTHER'

    def _parse_maturity_date(self, maturity_str: str) -> Optional[date]:
        """Parse IBKR maturity date string to date object."""
        try:
            if not maturity_str or len(maturity_str) != 8:
                return None
            # YYYYMMDD format
            year = int(maturity_str[:4])
            month = int(maturity_str[4:6])
            day = int(maturity_str[6:8])
            return date(year, month, day)
        except (ValueError, TypeError):
            return None