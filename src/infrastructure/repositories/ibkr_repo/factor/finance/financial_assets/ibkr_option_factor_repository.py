"""
IBKR Option Factor Repository - Interactive Brokers implementation for OptionFactor entities.

This repository handles option factor data from IBKR API,
applying IBKR-specific business rules before delegating persistence to local repository.
"""

from typing import Optional, List, Dict, Any
from datetime import date

from src.domain.ports.factor.option_factor_port import OptionFactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.finance.financial_assets.derivatives.option.option_factor import OptionFactor
from src.infrastructure.repositories.ibkr_repo.tick_types.ibkr_tick_mapping import IBKRTickFactorMapper, IBKRTickType


class IBKROptionFactorRepository(BaseIBKRFactorRepository, OptionFactorPort):
    """
    IBKR implementation of OptionFactorPort.
    Handles option factor data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR Option Factor Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            factory: Repository factory for dependency injection (optional)
        """
        super().__init__(ibkr_client)
        self.factory = factory
        
    @property
    def entity_class(self):
        return OptionFactor

    @property
    def local_repo(self):
        """Get local option factor repository for delegation."""
        if self.factory:
            return self.factory._local_repositories.get('option_factor')
        return None

    # OptionFactorPort interface implementation (delegate to local repository)
    
    def get_by_id(self, entity_id: int) -> Optional[OptionFactor]:
        """Get option factor by ID (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_id(entity_id)
        return None

    def get_by_name(self, name: str) -> Optional[OptionFactor]:
        """Get option factor by name (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_name(name)
        return None

    def get_by_underlying_symbol(self, symbol: str) -> List[OptionFactor]:
        """Get option factors by underlying asset symbol (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_underlying_symbol(symbol)
        return []

    def get_by_option_type(self, option_type: str) -> List[OptionFactor]:
        """Get option factors by option type (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_option_type(option_type)
        return []

    def get_by_strike_range(self, min_strike: Optional[float] = None, max_strike: Optional[float] = None) -> List[OptionFactor]:
        """Get option factors by strike price range (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_strike_range(min_strike, max_strike)
        return []

    def get_by_expiration_range(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[OptionFactor]:
        """Get option factors by expiration date range (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_expiration_range(start_date, end_date)
        return []

    def get_by_moneyness(self, moneyness_type: str) -> List[OptionFactor]:
        """Get option factors by moneyness (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_moneyness(moneyness_type)
        return []

    def get_by_group(self, group: str) -> List[OptionFactor]:
        """Get option factors by group (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_group(group)
        return []

    def get_all(self) -> List[OptionFactor]:
        """Get all option factors (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_all()
        return []

    def add(self, entity: OptionFactor) -> Optional[OptionFactor]:
        """Add option factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.add(entity)
        return None

    def update(self, entity: OptionFactor) -> Optional[OptionFactor]:
        """Update option factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.update(entity)
        return None

    def delete(self, entity_id: int) -> bool:
        """Delete option factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.delete(entity_id)
        return False

    def get_or_create_from_tick_type(self, tick_type: IBKRTickType, contract_data: Optional[Dict[str, Any]] = None) -> Optional[OptionFactor]:
        """
        Get or create an option factor from IBKR tick type.
        
        Args:
            tick_type: IBKR tick type enum (e.g., IBKRTickType.IMPLIED_VOLATILITY, IBKRTickType.DELTA)
            contract_data: Optional contract details from IBKR API
            
        Returns:
            OptionFactor entity from database or newly created
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
            
            # Create new option factor from IBKR tick mapping
            new_factor = OptionFactor(
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
                if 'strike' in contract_data:
                    new_factor.definition += f" - Strike: {contract_data['strike']}"
                if 'right' in contract_data:
                    new_factor.definition += f" - Type: {contract_data['right']}"
                if 'lastTradeDateOrContractMonth' in contract_data:
                    new_factor.definition += f" - Expiry: {contract_data['lastTradeDateOrContractMonth']}"
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    print(f"Created new option factor: {created_factor.name} (ID: {created_factor.id})")
                    return created_factor
            
            print(f"Failed to create option factor: {factor_mapping.factor_name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create_from_tick_type for tick type {tick_type}: {e}")
            return None

    def get_or_create(self, name: str, group: str = "derivatives", subgroup: str = "options") -> Optional[OptionFactor]:
        """
        Get or create an option factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "derivatives")
            subgroup: Factor subgroup (default: "options")
            
        Returns:
            OptionFactor entity from database or newly created
        """
        try:
            # Check if factor already exists by name
            if self.local_repo:
                existing_factor = self.local_repo.get_by_name(name)
                if existing_factor:
                    return existing_factor
            
            # Create new option factor
            new_factor = OptionFactor(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type="numeric",
                source="IBKR",
                definition=f"Option factor: {name} (from IBKR data)"
            )
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    print(f"Created new option factor: {created_factor.name} (ID: {created_factor.id})")
                    return created_factor
            
            print(f"Failed to create option factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for option factor {name}: {e}")
            return None

    def _extract_value_for_factor(self, factor_id: int, ibkr_data: Dict[str, Any]) -> Optional[Any]:
        """
        Extract option factor value from IBKR data.
        
        Args:
            factor_id: The factor ID
            ibkr_data: Raw IBKR data dictionary
            
        Returns:
            Extracted value or None if not available
        """
        try:
            # For option factors, extract Greeks and pricing data
            if 'impliedVol' in ibkr_data:
                return float(ibkr_data['impliedVol'])
            elif 'delta' in ibkr_data:
                return float(ibkr_data['delta'])
            elif 'gamma' in ibkr_data:
                return float(ibkr_data['gamma'])
            elif 'theta' in ibkr_data:
                return float(ibkr_data['theta'])
            elif 'vega' in ibkr_data:
                return float(ibkr_data['vega'])
            elif 'rho' in ibkr_data:
                return float(ibkr_data['rho'])
            elif 'lastPrice' in ibkr_data:
                return float(ibkr_data['lastPrice'])
            elif 'bid' in ibkr_data:
                return float(ibkr_data['bid'])
            elif 'ask' in ibkr_data:
                return float(ibkr_data['ask'])
            elif 'volume' in ibkr_data:
                return int(ibkr_data['volume'])
            elif 'openInterest' in ibkr_data:
                return int(ibkr_data['openInterest'])
            
            return None
            
        except (ValueError, TypeError) as e:
            print(f"Error converting option factor value: {e}")
            return None
        except Exception as e:
            print(f"Error extracting option factor value: {e}")
            return None