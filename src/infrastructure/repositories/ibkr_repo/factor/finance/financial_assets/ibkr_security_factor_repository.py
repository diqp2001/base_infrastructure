"""
IBKR Security Factor Repository - Interactive Brokers implementation for SecurityFactor entities.

This repository handles security factor data from IBKR API,
applying IBKR-specific business rules before delegating persistence to local repository.
"""

from typing import Optional, List, Dict, Any
from datetime import date

from src.domain.ports.factor.security_factor_port import SecurityFactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.finance.financial_assets.security_factor import SecurityFactor
from src.infrastructure.repositories.ibkr_repo.tick_types.ibkr_tick_mapping import IBKRTickFactorMapper, IBKRTickType


class IBKRSecurityFactorRepository(BaseIBKRFactorRepository, SecurityFactorPort):
    """
    IBKR implementation of SecurityFactorPort.
    Handles security factor data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR Security Factor Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            factory: Repository factory for dependency injection (optional)
        """
        super().__init__(ibkr_client)
        self.factory = factory
        
    @property
    def entity_class(self):
        return SecurityFactor

    @property
    def local_repo(self):
        """Get local security factor repository for delegation."""
        if self.factory:
            return self.factory._local_repositories.get('security_factor')
        return None

    # SecurityFactorPort interface implementation (delegate to local repository)
    
    def get_by_id(self, entity_id: int) -> Optional[SecurityFactor]:
        """Get security factor by ID (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_id(entity_id)
        return None

    def get_by_name(self, name: str) -> Optional[SecurityFactor]:
        """Get security factor by name (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_name(name)
        return None

    def get_by_symbol(self, symbol: str) -> List[SecurityFactor]:
        """Get security factors by symbol (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_symbol(symbol)
        return []

    def get_by_exchange(self, exchange: str) -> List[SecurityFactor]:
        """Get security factors by exchange (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_exchange(exchange)
        return []

    def get_by_sector(self, sector: str) -> List[SecurityFactor]:
        """Get security factors by sector (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_sector(sector)
        return []

    def get_by_market_cap_range(self, min_cap: Optional[float] = None, max_cap: Optional[float] = None) -> List[SecurityFactor]:
        """Get security factors by market capitalization range (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_market_cap_range(min_cap, max_cap)
        return []

    def get_by_security_type(self, security_type: str) -> List[SecurityFactor]:
        """Get security factors by security type (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_security_type(security_type)
        return []

    def get_by_group(self, group: str) -> List[SecurityFactor]:
        """Get security factors by group (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_group(group)
        return []

    def get_all(self) -> List[SecurityFactor]:
        """Get all security factors (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_all()
        return []

    def add(self, entity: SecurityFactor) -> Optional[SecurityFactor]:
        """Add security factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.add(entity)
        return None

    def update(self, entity: SecurityFactor) -> Optional[SecurityFactor]:
        """Update security factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.update(entity)
        return None

    def delete(self, entity_id: int) -> bool:
        """Delete security factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.delete(entity_id)
        return False

    def get_or_create_from_tick_type(self, tick_type: IBKRTickType, contract_data: Optional[Dict[str, Any]] = None) -> Optional[SecurityFactor]:
        """
        Get or create a security factor from IBKR tick type.
        
        Args:
            tick_type: IBKR tick type enum (e.g., IBKRTickType.LAST_PRICE)
            contract_data: Optional contract details from IBKR API
            
        Returns:
            SecurityFactor entity from database or newly created
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
            
            # Create new security factor from IBKR tick mapping
            new_factor = SecurityFactor(
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
                if 'secType' in contract_data:
                    new_factor.definition += f" - Type: {contract_data['secType']}"
                if 'exchange' in contract_data:
                    new_factor.definition += f" - Exchange: {contract_data['exchange']}"
                if 'primaryExchange' in contract_data:
                    new_factor.definition += f" - Primary Exchange: {contract_data['primaryExchange']}"
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    print(f"Created new security factor: {created_factor.name} (ID: {created_factor.id})")
                    return created_factor
            
            print(f"Failed to create security factor: {factor_mapping.factor_name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create_from_tick_type for tick type {tick_type}: {e}")
            return None

    def get_or_create(self, name: str, group: str = "security", subgroup: str = "general") -> Optional[SecurityFactor]:
        """
        Get or create a security factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "security")
            subgroup: Factor subgroup (default: "general")
            
        Returns:
            SecurityFactor entity from database or newly created
        """
        try:
            # Check if factor already exists by name
            if self.local_repo:
                existing_factor = self.local_repo.get_by_name(name)
                if existing_factor:
                    return existing_factor
            
            # Create new security factor
            new_factor = SecurityFactor(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type="numeric",
                source="IBKR",
                definition=f"Security factor: {name} (from IBKR data)"
            )
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    print(f"Created new security factor: {created_factor.name} (ID: {created_factor.id})")
                    return created_factor
            
            print(f"Failed to create security factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for security factor {name}: {e}")
            return None

    def _extract_value_for_factor(self, factor_id: int, ibkr_data: Dict[str, Any]) -> Optional[Any]:
        """
        Extract security factor value from IBKR data.
        
        Args:
            factor_id: The factor ID
            ibkr_data: Raw IBKR data dictionary
            
        Returns:
            Extracted value or None if not available
        """
        try:
            # For security factors, extract pricing, volume, and fundamental data
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
            elif 'high' in ibkr_data:
                return float(ibkr_data['high'])
            elif 'low' in ibkr_data:
                return float(ibkr_data['low'])
            elif 'open' in ibkr_data:
                return float(ibkr_data['open'])
            elif 'marketCap' in ibkr_data:
                return float(ibkr_data['marketCap'])
            elif 'peRatio' in ibkr_data:
                return float(ibkr_data['peRatio'])
            elif 'dividendYield' in ibkr_data:
                return float(ibkr_data['dividendYield'])
            elif 'beta' in ibkr_data:
                return float(ibkr_data['beta'])
            
            return None
            
        except (ValueError, TypeError) as e:
            print(f"Error converting security factor value: {e}")
            return None
        except Exception as e:
            print(f"Error extracting security factor value: {e}")
            return None