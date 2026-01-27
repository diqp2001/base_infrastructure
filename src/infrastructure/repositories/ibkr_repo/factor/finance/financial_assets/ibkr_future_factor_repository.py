"""
IBKR Future Factor Repository - Interactive Brokers implementation for FutureFactor entities.

This repository handles future factor data from IBKR API,
applying IBKR-specific business rules before delegating persistence to local repository.
"""

from typing import Optional, List, Dict, Any
from datetime import date

from src.domain.ports.factor.future_factor_port import FutureFactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor
from src.infrastructure.repositories.ibkr_repo.tick_types.ibkr_tick_mapping import IBKRTickFactorMapper, IBKRTickType


class IBKRFutureFactorRepository(BaseIBKRFactorRepository, FutureFactorPort):
    """
    IBKR implementation of FutureFactorPort.
    Handles future factor data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR Future Factor Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            factory: Repository factory for dependency injection (optional)
        """
        super().__init__(ibkr_client)
        self.factory = factory
        
    @property
    def entity_class(self):
        return FutureFactor

    @property
    def local_repo(self):
        """Get local future factor repository for delegation."""
        if self.factory:
            return self.factory._local_repositories.get('future_factor')
        return None

    # FutureFactorPort interface implementation (delegate to local repository)
    
    def get_by_id(self, entity_id: int) -> Optional[FutureFactor]:
        """Get future factor by ID (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_id(entity_id)
        return None

    def get_by_name(self, name: str) -> Optional[FutureFactor]:
        """Get future factor by name (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_name(name)
        return None

    def get_by_underlying_symbol(self, symbol: str) -> List[FutureFactor]:
        """Get future factors by underlying asset symbol (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_underlying_symbol(symbol)
        return []

    def get_by_contract_month(self, contract_month: str) -> List[FutureFactor]:
        """Get future factors by contract month (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_contract_month(contract_month)
        return []

    def get_by_exchange(self, exchange: str) -> List[FutureFactor]:
        """Get future factors by exchange (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_exchange(exchange)
        return []

    def get_by_roll_yield_range(self, min_yield: Optional[float] = None, max_yield: Optional[float] = None) -> List[FutureFactor]:
        """Get future factors by roll yield range (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_roll_yield_range(min_yield, max_yield)
        return []

    def get_by_group(self, group: str) -> List[FutureFactor]:
        """Get future factors by group (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_group(group)
        return []

    def get_all(self) -> List[FutureFactor]:
        """Get all future factors (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_all()
        return []

    def add(self, entity: FutureFactor) -> Optional[FutureFactor]:
        """Add future factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.add(entity)
        return None

    def update(self, entity: FutureFactor) -> Optional[FutureFactor]:
        """Update future factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.update(entity)
        return None

    def delete(self, entity_id: int) -> bool:
        """Delete future factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.delete(entity_id)
        return False

    def get_or_create_from_tick_type(self, tick_type: IBKRTickType, contract_data: Optional[Dict[str, Any]] = None) -> Optional[FutureFactor]:
        """
        Get or create a future factor from IBKR tick type.
        
        Args:
            tick_type: IBKR tick type enum (e.g., IBKRTickType.LAST_PRICE)
            contract_data: Optional contract details from IBKR API
            
        Returns:
            FutureFactor entity from database or newly created
        """
        try:
            # Get factor mapping configuration from IBKR tick type
            factor_mapping = IBKRTickFactorMapper.get_factor_mapping(tick_type)
            if not factor_mapping:
                print(f"No factor mapping found for tick type {tick_type}")
                return None
            
            # Check if factor already exists by name
            if self.local_repo:
                existing_factor = self.local_repo.get_by_name(factor_mapping.factor_name)
                if existing_factor:
                    return existing_factor
            
            # Create new future factor from IBKR tick mapping
            new_factor = FutureFactor(
                name=factor_mapping.factor_name,
                group=factor_mapping.factor_group,
                subgroup=factor_mapping.factor_subgroup,
                data_type=factor_mapping.data_type,
                source="IBKR",
                definition=f"{factor_mapping.description} (IBKR Tick Type {tick_type.value})"
            )
            
            # Add additional metadata from contract data if available
            if contract_data:
                if 'symbol' in contract_data:
                    new_factor.definition += f" - Symbol: {contract_data['symbol']}"
                if 'lastTradeDateOrContractMonth' in contract_data:
                    new_factor.definition += f" - Contract: {contract_data['lastTradeDateOrContractMonth']}"
                if 'exchange' in contract_data:
                    new_factor.definition += f" - Exchange: {contract_data['exchange']}"
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    print(f"Created new future factor: {created_factor.name} (ID: {created_factor.id})")
                    return created_factor
            
            print(f"Failed to create future factor: {factor_mapping.factor_name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create_from_tick_type for tick type {tick_type}: {e}")
            return None

    def get_or_create(self, name: str, group: str = "derivatives", subgroup: str = "futures") -> Optional[FutureFactor]:
        """
        Get or create a future factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "derivatives")
            subgroup: Factor subgroup (default: "futures")
            
        Returns:
            FutureFactor entity from database or newly created
        """
        try:
            # Check if factor already exists by name
            if self.local_repo:
                existing_factor = self.local_repo.get_by_name(name)
                if existing_factor:
                    return existing_factor
            
            # Create new future factor
            new_factor = FutureFactor(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type="numeric",
                source="IBKR",
                definition=f"Future factor: {name} (from IBKR data)"
            )
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    print(f"Created new future factor: {created_factor.name} (ID: {created_factor.id})")
                    return created_factor
            
            print(f"Failed to create future factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for future factor {name}: {e}")
            return None

    def _extract_value_for_factor(self, factor_id: int, ibkr_data: Dict[str, Any]) -> Optional[Any]:
        """
        Extract future factor value from IBKR data.
        
        Args:
            factor_id: The factor ID
            ibkr_data: Raw IBKR data dictionary
            
        Returns:
            Extracted value or None if not available
        """
        try:
            # For future factors, extract price, volume, and roll yield data
            if 'lastPrice' in ibkr_data:
                return float(ibkr_data['lastPrice'])
            elif 'close' in ibkr_data:
                return float(ibkr_data['close'])
            elif 'bid' in ibkr_data:
                return float(ibkr_data['bid'])
            elif 'ask' in ibkr_data:
                return float(ibkr_data['ask'])
            elif 'volume' in ibkr_data:
                return int(ibkr_data['volume'])
            elif 'openInterest' in ibkr_data:
                return int(ibkr_data['openInterest'])
            elif 'high' in ibkr_data:
                return float(ibkr_data['high'])
            elif 'low' in ibkr_data:
                return float(ibkr_data['low'])
            elif 'open' in ibkr_data:
                return float(ibkr_data['open'])
            
            return None
            
        except (ValueError, TypeError) as e:
            print(f"Error converting future factor value: {e}")
            return None
        except Exception as e:
            print(f"Error extracting future factor value: {e}")
            return None