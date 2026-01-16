"""
IBKR Instrument Repository - Interactive Brokers implementation for Instruments.

This repository handles instrument creation from IBKR contracts and manages
the flow: IBKR Contract → Instrument → Factor Values → Local Repository → DB
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date

from ibapi.contract import Contract, ContractDetails

from src.domain.ports.finance.instrument_port import InstrumentPort
from src.domain.ports.finance.financial_assets.financial_asset_port import FinancialAssetPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_repository import BaseIBKRRepository
from src.domain.entities.finance.instrument.ibkr_instrument import IBKRInstrument
from src.domain.entities.finance.instrument.instrument import Instrument

from ..services.contract_instrument_mapper import IBKRContractInstrumentMapper
from ..tick_types.ibkr_tick_mapping import IBKRTickType

# Forward references for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.infrastructure.repositories.ibkr_repo.factor.ibkr_instrument_factor_repository import IBKRInstrumentFactorRepository


class IBKRInstrumentRepository(BaseIBKRRepository, InstrumentPort):
    """
    IBKR implementation of InstrumentPort.
    
    This repository:
    1. Creates instruments from IBKR contracts
    2. Maps IBKR tick data to factor values
    3. Links instrument factor values to financial asset factor values
    4. Delegates persistence to local repositories
    """

    def __init__(
        self, 
        ibkr_client,
        local_instrument_repo: InstrumentPort,
        financial_asset_repo: FinancialAssetPort,
        factor_repo: Optional['IBKRInstrumentFactorRepository'] = None
    ):
        """
        Initialize IBKR Instrument Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            local_instrument_repo: Local repository for instrument persistence
            financial_asset_repo: Repository for financial asset lookups
            factor_repo: IBKR instrument factor repository for factor operations (optional)
        """
        super().__init__(ibkr_client)
        self.local_instrument_repo = local_instrument_repo
        self.financial_asset_repo = financial_asset_repo
        self.factor_repo = factor_repo
        self.contract_mapper = IBKRContractInstrumentMapper()
    @property
    def entity_class(self):
        
        return IBKRInstrument
    def get_or_create_from_contract(
        self,
        contract: Contract,
        contract_details: ContractDetails,
        tick_data: Optional[Dict[int, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> Optional[IBKRInstrument]:
        """
        Create an instrument from IBKR contract and optionally create factor values from tick data.
        
        This is the main method that implements the user's requested flow:
        1. Contract → Instrument
        2. Tick Data → Factor Values
        3. Instrument Factor Values → Financial Asset Factor Values
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object
            tick_data: Optional dictionary of tick_type_id -> value
            timestamp: When the data was captured
            
        Returns:
            IBKRInstrument entity or None if creation failed
        """
        try:
            timestamp = timestamp or datetime.now()
            
            # 1. Get or resolve the underlying financial asset
            asset = self._resolve_financial_asset(contract, contract_details)
            if not asset:
                print(f"Could not resolve financial asset for contract {contract.symbol}")
                return None
            
            # 2. Check if instrument already exists
            existing_instruments = self.local_instrument_repo.get_by_asset_and_source(
                asset.id, "IBKR"
            )
            if existing_instruments:
                # Use most recent instrument
                existing_instrument = max(existing_instruments, key=lambda x: x.date)
                if isinstance(existing_instrument, IBKRInstrument):
                    instrument = existing_instrument
                else:
                    # Convert regular Instrument to IBKRInstrument if needed
                    instrument = self._convert_to_ibkr_instrument(existing_instrument)
            else:
                # 3. Create new instrument from contract
                instrument = self.contract_mapper.contract_to_instrument(
                    contract, contract_details, asset, timestamp
                )
                if not instrument:
                    return None
                
                # 4. Persist instrument via local repository
                persisted_instrument = self.local_instrument_repo.add(instrument)
                if not persisted_instrument:
                    print(f"Failed to persist instrument for {contract.symbol}")
                    return None
                
                # Update instrument with persisted ID
                instrument.id = persisted_instrument.id
            
            # 5. Create factor values from tick data if provided
            if tick_data and self.factor_repo:
                factor_values = self.factor_repo.create_factor_values_from_ticks(
                    instrument, tick_data, timestamp
                )
                
                # 6. Map instrument factor values to financial asset factor values
                self.factor_repo.map_to_financial_asset_factors(instrument, factor_values, asset)
            
            return instrument
            
        except Exception as e:
            print(f"Error in get_or_create_from_contract for {contract.symbol}: {e}")
            return None
    
    def create_factor_values_from_ticks(
        self,
        instrument: IBKRInstrument,
        tick_data: Dict[int, Any],
        timestamp: Optional[datetime] = None
    ):
        """
        Create factor values from IBKR tick data for an existing instrument.
        
        This method is now delegated to IBKRInstrumentFactorRepository.
        """
        if not self.factor_repo:
            print("Factor repository not available")
            return []
        return self.factor_repo.create_factor_values_from_ticks(instrument, tick_data, timestamp)
    
    def get_supported_tick_types(self) -> List[IBKRTickType]:
        """Get list of tick types supported for factor mapping."""
        if not self.factor_repo:
            return []
        return self.factor_repo.get_supported_tick_types()
    
    def is_tick_type_supported(self, tick_type: IBKRTickType) -> bool:
        """Check if a tick type is supported for factor mapping."""
        if not self.factor_repo:
            return False
        return self.factor_repo.is_tick_type_supported(tick_type)
    
    # InstrumentPort interface implementation (delegate to local repository)
    
    def get_by_id(self, entity_id: int) -> Optional[Instrument]:
        """Get instrument by ID (delegates to local repository)."""
        return self.local_instrument_repo.get_by_id(entity_id)

    def get_by_asset_id(self, asset_id: int) -> List[Instrument]:
        """Get instruments by asset ID (delegates to local repository)."""
        return self.local_instrument_repo.get_by_asset_id(asset_id)

    def get_by_source(self, source: str) -> List[Instrument]:
        """Get instruments by source (delegates to local repository)."""
        return self.local_instrument_repo.get_by_source(source)

    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Instrument]:
        """Get instruments within date range (delegates to local repository)."""
        return self.local_instrument_repo.get_by_date_range(start_date, end_date)

    def get_by_asset_and_source(self, asset_id: int, source: str) -> List[Instrument]:
        """Get instruments by asset and source (delegates to local repository)."""
        return self.local_instrument_repo.get_by_asset_and_source(asset_id, source)

    def get_latest_by_asset(self, asset_id: int) -> Optional[Instrument]:
        """Get latest instrument for asset (delegates to local repository)."""
        return self.local_instrument_repo.get_latest_by_asset(asset_id)

    def get_all(self) -> List[Instrument]:
        """Get all instruments (delegates to local repository)."""
        return self.local_instrument_repo.get_all()

    def add(self, entity: Instrument) -> Optional[Instrument]:
        """Add instrument (delegates to local repository)."""
        return self.local_instrument_repo.add(entity)

    def update(self, entity: Instrument) -> Optional[Instrument]:
        """Update instrument (delegates to local repository)."""
        return self.local_instrument_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete instrument (delegates to local repository)."""
        return self.local_instrument_repo.delete(entity_id)

    def count_by_source(self, source: str) -> int:
        """Count instruments by source (delegates to local repository)."""
        return self.local_instrument_repo.count_by_source(source)

    def get_unique_sources(self) -> List[str]:
        """Get unique sources (delegates to local repository)."""
        return self.local_instrument_repo.get_unique_sources()
    
    # Private helper methods
    
    def _resolve_financial_asset(self, contract: Contract, contract_details: ContractDetails):
        """
        Resolve the underlying financial asset for the contract.
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object
            
        Returns:
            FinancialAsset entity or None if not found/created
        """
        try:
            # This would depend on your financial asset resolution logic
            # For example, for stocks you might look up by symbol
            if contract.secType == "STK":
                # Look up company share by symbol
                company_shares = self.financial_asset_repo.get_by_ticker(contract.symbol)
                if company_shares and len(company_shares) > 0:
                    return company_shares[0]
            
            # Could implement similar logic for other asset types (bonds, futures, etc.)
            
            print(f"Could not resolve financial asset for contract {contract.symbol} ({contract.secType})")
            return None
            
        except Exception as e:
            print(f"Error resolving financial asset: {e}")
            return None
    
    # Factor-related methods removed - now handled by IBKRInstrumentFactorRepository
    
    def _convert_to_ibkr_instrument(self, instrument: Instrument) -> IBKRInstrument:
        """Convert a regular Instrument to IBKRInstrument if possible."""
        try:
            return IBKRInstrument(
                id=instrument.id,
                asset=instrument.asset,
                source=instrument.source,
                date=instrument.date,
                # Other IBKR-specific fields will be empty but that's OK
            )
        except Exception as e:
            print(f"Error converting instrument to IBKRInstrument: {e}")
            return instrument