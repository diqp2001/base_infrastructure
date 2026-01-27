"""
IBKR Share Factor Repository - Interactive Brokers implementation for ShareFactor entities.

This repository handles share factor data from IBKR API,
applying IBKR-specific business rules before delegating persistence to local repository.
"""

from typing import Optional, List, Dict, Any
from datetime import date

from src.domain.ports.factor.share_factor_port import ShareFactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor
from src.infrastructure.repositories.ibkr_repo.tick_types.ibkr_tick_mapping import IBKRTickFactorMapper, IBKRTickType


class IBKRShareFactorRepository(BaseIBKRFactorRepository, ShareFactorPort):
    """
    IBKR implementation of ShareFactorPort.
    Handles share factor data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR Share Factor Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            factory: Repository factory for dependency injection (optional)
        """
        super().__init__(ibkr_client)
        self.factory = factory
        
    @property
    def entity_class(self):
        return ShareFactor

    @property
    def local_repo(self):
        """Get local share factor repository for delegation."""
        if self.factory:
            return self.factory._local_repositories.get('share_factor')
        return None

    # ShareFactorPort interface implementation (delegate to local repository)
    
    def get_by_id(self, entity_id: int) -> Optional[ShareFactor]:
        """Get share factor by ID (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_id(entity_id)
        return None

    def get_by_name(self, name: str) -> Optional[ShareFactor]:
        """Get share factor by name (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_name(name)
        return None

    def get_by_group(self, group: str) -> List[ShareFactor]:
        """Get share factors by group (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_group(group)
        return []

    def get_by_subgroup(self, subgroup: str) -> List[ShareFactor]:
        """Get share factors by subgroup (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_subgroup(subgroup)
        return []

    def get_all(self) -> List[ShareFactor]:
        """Get all share factors (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_all()
        return []

    def add(self, entity: ShareFactor) -> Optional[ShareFactor]:
        """Add share factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.add(entity)
        return None

    def update(self, entity_id: int, **kwargs) -> Optional[ShareFactor]:
        """Update share factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.update(entity_id, **kwargs)
        return None

    def delete(self, entity_id: int) -> bool:
        """Delete share factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.delete(entity_id)
        return False

    def get_or_create_from_tick_type(self, tick_type: IBKRTickType, contract_data: Optional[Dict[str, Any]] = None) -> Optional[ShareFactor]:
        """
        Get or create a share factor from IBKR tick type.
        
        Args:
            tick_type: IBKR tick type enum (e.g., IBKRTickType.VOLUME)
            contract_data: Optional contract details from IBKR API
            
        Returns:
            ShareFactor entity from database or newly created
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
            
            # Create new share factor from IBKR tick mapping
            new_factor = ShareFactor(
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
                if 'exchange' in contract_data:
                    new_factor.definition += f" - Exchange: {contract_data['exchange']}"
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    print(f"Created new share factor: {created_factor.name} (ID: {created_factor.id})")
                    return created_factor
            
            print(f"Failed to create share factor: {factor_mapping.factor_name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create_from_tick_type for tick type {tick_type}: {e}")
            return None

    def get_or_create(self, name: str, group: str = "price", subgroup: str = "share") -> Optional[ShareFactor]:
        """
        Get or create a share factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "price")
            subgroup: Factor subgroup (default: "share")
            
        Returns:
            ShareFactor entity from database or newly created
        """
        try:
            # Check if factor already exists by name
            if self.local_repo:
                existing_factor = self.local_repo.get_by_name(name)
                if existing_factor:
                    return existing_factor
            
            # Create new share factor
            new_factor = ShareFactor(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type="numeric",
                source="IBKR",
                definition=f"Share factor: {name} (from IBKR data)"
            )
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    print(f"Created new share factor: {created_factor.name} (ID: {created_factor.id})")
                    return created_factor
            
            print(f"Failed to create share factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for share factor {name}: {e}")
            return None

    def create_price_factors(self, symbol: str) -> List[ShareFactor]:
        """
        Convenience method to create common price factors for a share.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of created ShareFactor entities
        """
        factors = []
        price_types = [
            ("Open", IBKRTickType.OPEN_TICK),
            ("High", IBKRTickType.HIGH),
            ("Low", IBKRTickType.LOW),
            ("Close", IBKRTickType.CLOSE_PRICE),
            ("Volume", IBKRTickType.VOLUME)
        ]
        
        for factor_name, tick_type in price_types:
            contract_data = {'symbol': symbol}
            factor = self.get_or_create_from_tick_type(tick_type, contract_data)
            if factor:
                factors.append(factor)
        
        return factors

    def _extract_value_for_factor(self, factor_id: int, ibkr_data: Dict[str, Any]) -> Optional[Any]:
        """
        Extract share factor value from IBKR data.
        
        Args:
            factor_id: The factor ID
            ibkr_data: Raw IBKR data dictionary
            
        Returns:
            Extracted value or None if not available
        """
        try:
            # For share factors, extract comprehensive market data
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
            elif 'avgVolume' in ibkr_data:
                return int(ibkr_data['avgVolume'])
            elif 'marketCap' in ibkr_data:
                return float(ibkr_data['marketCap'])
            elif 'peRatio' in ibkr_data:
                return float(ibkr_data['peRatio'])
            elif 'dividend' in ibkr_data:
                return float(ibkr_data['dividend'])
            
            return None
            
        except (ValueError, TypeError) as e:
            print(f"Error converting share factor value: {e}")
            return None
        except Exception as e:
            print(f"Error extracting share factor value: {e}")
            return None