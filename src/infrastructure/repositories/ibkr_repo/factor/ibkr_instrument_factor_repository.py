"""
IBKR Instrument Factor Repository - Interactive Brokers implementation for Instrument factor operations.

This repository handles the creation of factor values from IBKR instruments and tick data,
implementing the core pipeline: Instrument + Tick Data → Factor Values.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, time

from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.finance.instrument.ibkr_instrument import IBKRInstrument
from src.infrastructure.repositories.ibkr_repo.tick_types.ibkr_tick_mapping import IBKRTickType, IBKRTickFactorMapper
from src.infrastructure.repositories.ibkr_repo.services.contract_instrument_mapper import IBKRContractInstrumentMapper


class IBKRInstrumentFactorRepository(BaseIBKRFactorRepository):
    """
    IBKR Instrument Factor Repository.
    
    Specialized repository that creates factor values from instruments and IBKR tick data.
    This handles the core transformation: Instrument + Tick Data → Factor Values.
    """

    def __init__(
        self, 
        ibkr_client, 
        factory
    ):
        """
        Initialize IBKR Instrument Factor Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            local_factor_value_repo: Local repository for factor value persistence
            local_instrument_repo: Local repository for instrument persistence
        """
        super().__init__(ibkr_client)
        self.local_instrument_repo = factory.instrument_ibkr_repo
        self.factory = factory
        self.tick_mapper = IBKRTickFactorMapper()
        self.contract_mapper = IBKRContractInstrumentMapper()

    @property
    def local_repo(self):
        """Get local factor value repository through factory."""
        if self.factory:
            return self.factory.factor_value_local_repo
        return None

    def create_factor_values_from_ticks(
        self,
        instrument: IBKRInstrument,
        tick_data: Dict[int, Any],
        timestamp: Optional[datetime] = None
    ) -> List[FactorValue]:
        """
        Create factor values from IBKR tick data for an instrument.
        
        This is the core method that implements:
        Instrument + Tick Data → Factor Values
        
        Args:
            instrument: IBKRInstrument entity
            tick_data: Dictionary of tick_type_id -> value
            timestamp: When the tick data was captured
            
        Returns:
            List of created FactorValue entities
        """
        try:
            timestamp = timestamp or datetime.now()
            
            # Convert tick data to factor values using the contract mapper
            factor_values = self.contract_mapper.tick_data_to_factor_values(
                instrument, tick_data, timestamp
            )
            
            # Persist factor values via local repository
            persisted_values = []
            for factor_value in factor_values:
                # Check if factor value already exists for this date
                date_str = factor_value.date.strftime('%Y-%m-%d')
                existing = self.local_repo.get_by_factor_entity_date(
                    factor_value.factor_id, factor_value.entity_id, date_str
                )
                if existing:
                    persisted_values.append(existing)
                else:
                    persisted = self.local_repo.add(factor_value)
                    if persisted:
                        persisted_values.append(persisted)
            
            return persisted_values
            
        except Exception as e:
            print(f"Error creating factor values from ticks: {e}")
            return []

    def create_factor_value_from_single_tick(
        self,
        instrument: IBKRInstrument,
        tick_type: IBKRTickType,
        tick_value: Any,
        timestamp: Optional[datetime] = None
    ) -> Optional[FactorValue]:
        """
        Create a single factor value from a specific IBKR tick.
        
        Args:
            instrument: IBKRInstrument entity
            tick_type: IBKR tick type enum
            tick_value: Value from IBKR tick
            timestamp: When the tick was captured
            
        Returns:
            FactorValue entity or None if creation failed
        """
        try:
            # Convert single tick to tick data dictionary
            tick_data = {tick_type.value: tick_value}
            
            # Use the multi-tick method
            factor_values = self.create_factor_values_from_ticks(instrument, tick_data, timestamp)
            
            # Return the first (and should be only) factor value created
            return factor_values[0] if factor_values else None
            
        except Exception as e:
            print(f"Error creating factor value from single tick: {e}")
            return None

    def map_to_financial_asset_factors(
        self,
        instrument: IBKRInstrument,
        instrument_factor_values: List[FactorValue],
        financial_asset
    ) -> List[FactorValue]:
        """
        Map instrument factor values to financial asset factor values.
        
        This creates the link between instrument-level factors (from IBKR ticks)
        and asset-level factors that can be used in analysis.
        
        Args:
            instrument: The IBKRInstrument entity
            instrument_factor_values: List of factor values from instrument
            financial_asset: The underlying financial asset
            
        Returns:
            List of created asset-level FactorValue entities
        """
        try:
            asset_factor_values = []
            
            for instrument_factor_value in instrument_factor_values:
                # Create corresponding factor value for the financial asset
                asset_factor_value = FactorValue(
                    id=None,  # Will be set by repository
                    factor_id=instrument_factor_value.factor_id,  # Same factor
                    entity_id=financial_asset.id,  # But linked to the asset, not instrument
                    date=instrument_factor_value.date,
                    value=instrument_factor_value.value
                )
                
                # Check if asset factor value already exists
                date_str = asset_factor_value.date.strftime('%Y-%m-%d')
                existing = self.local_repo.get_by_factor_entity_date(
                    asset_factor_value.factor_id, 
                    asset_factor_value.entity_id,
                    date_str
                )
                
                if not existing:
                    # Persist the asset-level factor value
                    persisted = self.local_repo.add(asset_factor_value)
                    if persisted:
                        asset_factor_values.append(persisted)
                else:
                    asset_factor_values.append(existing)
                    
            return asset_factor_values
            
        except Exception as e:
            print(f"Error mapping instrument factors to asset factors: {e}")
            return []

    def get_or_create(self, instrument: IBKRInstrument,contract,historical=True,factor= None,entity  = None,
                     timestamp: Optional[datetime] = None, what_to_show = "TRADES",  duration_str: str = "1 W", bar_size_setting: str = "5 secs",end_date_time: str = "") -> Optional[FactorValue]:
        """
        Get or create a factor value for an instrument from IBKR tick data.
        
        This method follows the established pattern:
        1. Check if factor value already exists
        2. If not, create from IBKR tick data
        3. Return the created/found factor value
        
        Args:
            instrument: IBKRInstrument entity
            tick_type: IBKR tick type for the factor
            tick_value: Value from IBKR tick
            timestamp: When the tick was captured (defaults to now)
            
        Returns:
            FactorValue entity or None if creation/retrieval failed
        """
        try:
            timestamp = timestamp or datetime.now()
            date_obj = timestamp.date()
            date_str = date_obj.strftime('%Y-%m-%d')
            
            # Get or create factor for this tick type
            
            
            
            
            # Check if factor value already exists for this instrument, factor, and date
            existing_value = self.local_repo.get_by_factor_entity_date(factor.id, entity.id, date_str)
            if existing_value:
                return existing_value
            
            if historical:
                tick_value = self.ib_client.get_historical_data(contract = contract,what_to_show=what_to_show,bar_size_setting=bar_size_setting,duration_str=duration_str)
                
            else:
                factor_mapping = self.tick_mapper.get_factor_mapping(factor.name)
                if not factor_mapping:
                    print(f"No factor mapping found for tick type {factor.name}")
                    return None
                tick_value = self.ib_client.get_market_data_snapshot(contract = contract,generic_tick_list=factor_mapping[0].value)
                
            return tick_value
            
        except Exception as e:
            print(f"Error in get_or_create for instrument factor: {e}")
            return None

    def get_supported_tick_types(self) -> List[IBKRTickType]:
        """Get list of tick types supported for factor mapping."""
        return self.tick_mapper.get_supported_tick_types()
    
    def is_tick_type_supported(self, tick_type: IBKRTickType) -> bool:
        """Check if a tick type is supported for factor mapping."""
        return self.tick_mapper.is_tick_type_supported(tick_type)
    
    def get_factor_mapping_for_tick(self, tick_type: IBKRTickType):
        """Get factor mapping configuration for a tick type."""
        return self.tick_mapper.get_factor_mapping(tick_type)

    def _extract_value_for_factor(self, factor_id: int, ibkr_data: Dict[str, Any]) -> Optional[Any]:
        """
        Extract factor value from IBKR instrument data.
        
        For instruments, this typically involves extracting values from
        tick data or contract details.
        """
        try:
            # Try to extract from tick data first
            tick_data = ibkr_data.get('tick_data', {})
            if tick_data and factor_id in tick_data:
                return tick_data[factor_id]
            
            # Try to extract from instrument metadata
            instrument = ibkr_data.get('instrument')
            if instrument:
                # Could implement instrument-specific factor extraction here
                pass
            
            return None
            
        except Exception as e:
            print(f"Error extracting factor value {factor_id} from instrument data: {e}")
            return None