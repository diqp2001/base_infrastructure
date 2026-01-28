"""
IBKR Financial Asset Factor Repository - Interactive Brokers implementation for FinancialAssetFactor entities.

This repository handles financial asset factor data from IBKR API,
applying IBKR-specific business rules before delegating persistence to local repository.
"""

from typing import Optional, List, Dict, Any
from datetime import date

from src.domain.ports.factor.financial_asset_factor_port import FinancialAssetFactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.finance.financial_assets.financial_asset_factor import FinancialAssetFactor
from src.infrastructure.repositories.ibkr_repo.tick_types.ibkr_tick_mapping import IBKRTickFactorMapper, IBKRTickType


class IBKRFinancialAssetFactorRepository(BaseIBKRFactorRepository, FinancialAssetFactorPort):
    """
    IBKR implementation of FinancialAssetFactorPort.
    Handles financial asset factor data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR Financial Asset Factor Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            factory: Repository factory for dependency injection (optional)
        """
        super().__init__(ibkr_client)
        self.factory = factory
        
    @property
    def entity_class(self):
        return FinancialAssetFactor

    @property
    def local_repo(self):
        """Get local financial asset factor repository for delegation."""
        if self.factory:
            return self.factory._local_repositories.get('financial_asset_factor')
        return None

    # FinancialAssetFactorPort interface implementation (delegate to local repository)
    
    def get_by_id(self, entity_id: int) -> Optional[FinancialAssetFactor]:
        """Get financial asset factor by ID (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_id(entity_id)
        return None

    def get_by_name(self, name: str) -> Optional[FinancialAssetFactor]:
        """Get financial asset factor by name (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_name(name)
        return None

    def get_by_asset_class(self, asset_class: str) -> List[FinancialAssetFactor]:
        """Get financial asset factors by asset class (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_asset_class(asset_class)
        return []

    def get_by_currency(self, currency: str) -> List[FinancialAssetFactor]:
        """Get financial asset factors by currency (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_currency(currency)
        return []

    def get_by_risk_level(self, risk_level: str) -> List[FinancialAssetFactor]:
        """Get financial asset factors by risk level (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_risk_level(risk_level)
        return []

    def get_by_liquidity_tier(self, tier: str) -> List[FinancialAssetFactor]:
        """Get financial asset factors by liquidity tier (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_liquidity_tier(tier)
        return []

    def get_by_group(self, group: str) -> List[FinancialAssetFactor]:
        """Get financial asset factors by group (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_group(group)
        return []

    def get_all(self) -> List[FinancialAssetFactor]:
        """Get all financial asset factors (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_all()
        return []

    def add(self, entity: FinancialAssetFactor) -> Optional[FinancialAssetFactor]:
        """Add financial asset factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.add(entity)
        return None

    def update(self, entity: FinancialAssetFactor) -> Optional[FinancialAssetFactor]:
        """Update financial asset factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.update(entity)
        return None

    def delete(self, entity_id: int) -> bool:
        """Delete financial asset factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.delete(entity_id)
        return False

    def get_or_create_from_tick_type(self, tick_type: IBKRTickType, contract_data: Optional[Dict[str, Any]] = None) -> Optional[FinancialAssetFactor]:
        """
        Get or create a financial asset factor from IBKR tick type.
        
        Args:
            tick_type: IBKR tick type enum (e.g., IBKRTickType.LAST_PRICE)
            contract_data: Optional contract details from IBKR API
            
        Returns:
            FinancialAssetFactor entity from database or newly created
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
            
            # Create new financial asset factor from IBKR tick mapping
            new_factor = FinancialAssetFactor(
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
                if 'currency' in contract_data:
                    new_factor.definition += f" - Currency: {contract_data['currency']}"
                if 'exchange' in contract_data:
                    new_factor.definition += f" - Exchange: {contract_data['exchange']}"
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    print(f"Created new financial asset factor: {created_factor.name} (ID: {created_factor.id})")
                    return created_factor
            
            print(f"Failed to create financial asset factor: {factor_mapping.factor_name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create_from_tick_type for tick type {tick_type}: {e}")
            return None

    def _create_or_get(self, name: str, group: str = "financial_asset", subgroup: str = "general") -> Optional[FinancialAssetFactor]:
        """
        Get or create a financial asset factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "financial_asset")
            subgroup: Factor subgroup (default: "general")
            
        Returns:
            FinancialAssetFactor entity from database or newly created
        """
        try:
            # Check if factor already exists by name
            if self.local_repo:
                existing_factor = self.local_repo.get_by_name(name)
                if existing_factor:
                    return existing_factor
            
            # Create new financial asset factor
            new_factor = FinancialAssetFactor(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type="numeric",
                source="IBKR",
                definition=f"Financial asset factor: {name} (from IBKR data)"
            )
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    print(f"Created new financial asset factor: {created_factor.name} (ID: {created_factor.id})")
                    return created_factor
            
            print(f"Failed to create financial asset factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for financial asset factor {name}: {e}")
            return None

    def _extract_value_for_factor(self, factor_id: int, ibkr_data: Dict[str, Any]) -> Optional[Any]:
        """
        Extract financial asset factor value from IBKR data.
        
        Args:
            factor_id: The factor ID
            ibkr_data: Raw IBKR data dictionary
            
        Returns:
            Extracted value or None if not available
        """
        try:
            # For financial asset factors, extract general pricing and volume data
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
            elif 'avgVolume' in ibkr_data:
                return int(ibkr_data['avgVolume'])
            
            return None
            
        except (ValueError, TypeError) as e:
            print(f"Error converting financial asset factor value: {e}")
            return None
        except Exception as e:
            print(f"Error extracting financial asset factor value: {e}")
            return None