"""
IBKR Factor Value Repository - Interactive Brokers implementation for FactorValue entities.

This repository handles factor value data acquisition from IBKR API,
implementing the pipelines for IBKR Contract → Instrument → Factor Values → Asset Factor Values.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date

from src.domain.ports.factor.factor_value_port import FactorValuePort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.factor_value import FactorValue
from src.infrastructure.repositories.ibkr_repo.tick_types.ibkr_tick_mapping import IBKRTickType, IBKRTickFactorMapper

# Forward references for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.infrastructure.repositories.ibkr_repo.finance.instrument_repository import IBKRInstrumentRepository
    from ibapi.contract import Contract, ContractDetails


class IBKRFactorValueRepository(BaseIBKRFactorRepository, FactorValuePort):
    """
    IBKR implementation of FactorValuePort.
    
    This repository implements the complete pipeline:
    1. IBKR Contract → Instrument (via IBKRInstrumentRepository)
    2. Extract tick data → Factor Values 
    3. Map Instrument Factor Values → Financial Asset Factor Values
    4. Delegate persistence to local repository
    """

    def __init__(
        self, 
        ibkr_client, 
        local_repo: FactorValuePort,
        ibkr_instrument_repo: Optional['IBKRInstrumentRepository'] = None
    ):
        """
        Initialize IBKR Factor Value Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            local_factor_value_repo: Local repository implementing FactorValuePort for persistence
            ibkr_instrument_repo: IBKR instrument repository for contract→instrument flow
        """
        super().__init__(ibkr_client, local_repo)
        self.ibkr_instrument_repo = ibkr_instrument_repo
        self.tick_mapper = IBKRTickFactorMapper()

    # Pipeline Methods - Main functionality requested by user

    def get_or_create_factor_value_with_ticks(
        self, 
        symbol_or_name: str, 
        factor_id: int, 
        time: str,
        tick_data: Optional[Dict[int, Any]] = None
    ) -> Optional[FactorValue]:
        """
        Get or create a factor value for a financial asset by symbol using IBKR API with instrument flow.
        
        This method follows the new architecture:
        1. Create IBKR Contract → Instrument
        2. Extract tick data → Factor Values 
        3. Map Instrument Factor Values → Financial Asset Factor Values
        
        Args:
            symbol_or_name: Stock symbol or asset name
            factor_id: The factor ID (integer)
            time: Date string in 'YYYY-MM-DD' format
            tick_data: Optional IBKR tick data dictionary (tick_type_id -> value)
            
        Returns:
            FactorValue entity or None if creation/retrieval failed
        """
        try:
            if not self._validate_factor_value_data(factor_id, 1, time):  # Entity ID validated later
                return None

            if not self.ibkr_instrument_repo:
                print("IBKR instrument repository not available, falling back to legacy method")
                return self.get_or_create_factor_value(symbol_or_name, factor_id, time)
            
            # 1. Get or create financial asset entity first (this depends on the calling repository)
            # For now, we assume entity_id = 1 as placeholder - this should be resolved by caller
            entity_id = 1  # This would be passed from the calling repository (e.g., CompanyShareRepository)
            
            # 2. Check if factor value already exists for this date
            existing = self._check_existing_factor_value(factor_id, entity_id, time)
            if existing:
                return existing
            
            # 3. Fetch IBKR contract
            contract = self._fetch_contract_for_symbol(symbol_or_name)
            if not contract:
                return None
                
            # 4. Get contract details from IBKR
            contract_details = self._fetch_contract_details(contract)
            if not contract_details:
                return None
            
            # 5. **NEW ARCHITECTURE**: Create instrument from contract and tick data
            timestamp = datetime.strptime(time, '%Y-%m-%d')
            instrument = self.ibkr_instrument_repo.get_or_create_from_contract(
                contract=contract,
                contract_details=contract_details,
                tick_data=tick_data,
                timestamp=timestamp
            )
            
            if not instrument:
                print(f"Failed to create instrument for {symbol_or_name}")
                return None
            
            # 6. The instrument creation process automatically creates factor values
            # and maps them to the financial asset 
            # So we just need to retrieve the specific factor value requested
            return self._check_existing_factor_value(factor_id, entity_id, time)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create_factor_value_with_ticks for {symbol_or_name}: {e}")
            return None
    
    def create_factor_value_from_tick_data(
        self,
        symbol: str,
        tick_type: IBKRTickType,
        tick_value: Any,
        time: str
    ) -> Optional[FactorValue]:
        """
        Create a factor value from specific IBKR tick data.
        
        Args:
            symbol: Stock symbol
            tick_type: IBKR tick type enum
            tick_value: Value from IBKR tick
            time: Date string in 'YYYY-MM-DD' format
            
        Returns:
            FactorValue entity or None if creation failed
        """
        try:
            # Convert single tick to tick data dictionary
            tick_data = {tick_type.value: tick_value}
            
            # Resolve factor_id from tick type
            factor_mapping = self.tick_mapper.get_factor_mapping(tick_type)
            if not factor_mapping:
                print(f"No factor mapping found for tick type {tick_type}")
                return None
                
            # For now, use tick_type value as factor_id (this could be refined)
            factor_id = tick_type.value
            
            # Use instrument-based method with tick data
            return self.get_or_create_factor_value_with_ticks(
                symbol_or_name=symbol,
                factor_id=factor_id,
                time=time,
                tick_data=tick_data
            )
            
        except Exception as e:
            print(f"Error creating factor value from tick data: {e}")
            return None

    def get_or_create_factor_value(self, symbol_or_name: str, factor_id: int, time: str) -> Optional[FactorValue]:
        """
        Get or create a factor value for an asset by symbol or name using IBKR API.
        
        Args:
            symbol_or_name: Stock symbol or asset name
            factor_id: The factor ID (integer)
            time: Date string in 'YYYY-MM-DD' format
            
        Returns:
            FactorValue entity or None if creation/retrieval failed
        """
        try:
            if not self._validate_factor_value_data(factor_id, 1, time):
                return None
                
            # For now, assume entity_id = 1 (should be resolved by caller)
            entity_id = 1
            
            # 1. Check if factor value already exists for this date
            existing = self._check_existing_factor_value(factor_id, entity_id, time)
            if existing:
                return existing
            
            # 2. Fetch info via contract from IBKR API
            contract = self._fetch_contract_for_symbol(symbol_or_name)
            if not contract:
                return None
                
            # 3. Get contract details from IBKR
            contract_details = self._fetch_contract_details(contract)
            if not contract_details:
                return None
                
            # 4. Apply IBKR-specific rules and convert to factor value
            factor_value = self._contract_to_factor_value(contract, contract_details, factor_id, entity_id, time)
            if not factor_value:
                return None
                
            # 5. Delegate persistence to local repository
            return self.local_repo.add(factor_value)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create_factor_value for {symbol_or_name}: {e}")
            return None

    # FactorValuePort interface implementation (delegate to local repository)

    def get_by_id(self, entity_id: int) -> Optional[FactorValue]:
        """Get factor value by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_by_factor_id(self, factor_id: int) -> List[FactorValue]:
        """Get factor values by factor ID (delegates to local repository)."""
        return self.local_repo.get_by_factor_id(factor_id)

    def get_by_entity_id(self, entity_id: int) -> List[FactorValue]:
        """Get factor values by entity ID (delegates to local repository)."""
        return self.local_repo.get_by_entity_id(entity_id)

    def get_by_date(self, date_obj: date) -> List[FactorValue]:
        """Get factor values by date (delegates to local repository)."""
        return self.local_repo.get_by_date(date_obj)

    def get_by_date_range(self, start_date: date, end_date: date) -> List[FactorValue]:
        """Get factor values by date range (delegates to local repository)."""
        return self.local_repo.get_by_date_range(start_date, end_date)

    def get_by_factor_entity(self, factor_id: int, entity_id: int) -> List[FactorValue]:
        """Get factor values by factor and entity (delegates to local repository)."""
        return self.local_repo.get_by_factor_entity(factor_id, entity_id)

    def get_by_factor_entity_date(self, factor_id: int, entity_id: int, date_str: str) -> Optional[FactorValue]:
        """Get factor value by factor, entity, and date (delegates to local repository)."""
        return self.local_repo.get_by_factor_entity_date(factor_id, entity_id, date_str)

    def get_all_dates_by_id_entity_id(self, factor_id: int, entity_id: int) -> List[str]:
        """Get all dates for factor and entity (delegates to local repository)."""
        return self.local_repo.get_all_dates_by_id_entity_id(factor_id, entity_id)

    def get_latest_by_factor_entity(self, factor_id: int, entity_id: int) -> Optional[FactorValue]:
        """Get latest factor value by factor and entity (delegates to local repository)."""
        return self.local_repo.get_latest_by_factor_entity(factor_id, entity_id)

    def get_time_series(self, factor_id: int, entity_id: int, start_date: date, end_date: date) -> List[FactorValue]:
        """Get time series data (delegates to local repository)."""
        return self.local_repo.get_time_series(factor_id, entity_id, start_date, end_date)

    def get_all(self) -> List[FactorValue]:
        """Get all factor values (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: FactorValue) -> Optional[FactorValue]:
        """Add factor value entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity_id: int, **kwargs) -> Optional[FactorValue]:
        """Update factor value entity (delegates to local repository)."""
        return self.local_repo.update(entity_id, **kwargs)

    def delete(self, entity_id: int) -> bool:
        """Delete factor value entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    # Private helper methods - IBKR-specific implementation

    def _fetch_contract_for_symbol(self, symbol_or_name: str) -> Optional['Contract']:
        """
        Fetch IBKR contract for symbol or name.
        
        Args:
            symbol_or_name: Stock symbol or asset name
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            from ibapi.contract import Contract
            
            contract = Contract()
            # Try as symbol first
            if len(symbol_or_name) <= 5 and symbol_or_name.isupper():
                contract.symbol = symbol_or_name
            else:
                # If it looks like a company name, assume it's a symbol
                contract.symbol = symbol_or_name.upper()
            
            contract.secType = "STK"
            contract.exchange = "SMART"
            contract.currency = "USD"
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR contract for {symbol_or_name}: {e}")
            return None

    def _fetch_contract_details(self, contract: 'Contract') -> Optional['ContractDetails']:
        """
        Fetch contract details from IBKR API.
        
        Args:
            contract: IBKR Contract object
            
        Returns:
            ContractDetails object or None if not found
        """
        try:
            from ibapi.contract import ContractDetails
            
            # This would involve an actual IBKR API call
            # For now, return a mock object to demonstrate the pattern
            # In real implementation, use self.ibkr_client.reqContractDetails()
            
            contract_details = ContractDetails()
            contract_details.contract = contract
            contract_details.marketName = "Stock Market"
            contract_details.minTick = 0.01
            contract_details.priceMagnifier = 1
            contract_details.longName = f"{contract.symbol} Inc."
            contract_details.industry = "Technology"
            contract_details.category = "Common Stock"
            
            return contract_details
        except Exception as e:
            print(f"Error fetching IBKR contract details: {e}")
            return None

    def _contract_to_factor_value(
        self, 
        contract: 'Contract', 
        contract_details: 'ContractDetails', 
        factor_id: int, 
        entity_id: int, 
        date_str: str
    ) -> Optional[FactorValue]:
        """
        Convert IBKR contract and details to a FactorValue domain entity.
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object
            factor_id: The factor ID
            entity_id: The entity ID
            date_str: Date string in 'YYYY-MM-DD' format
            
        Returns:
            FactorValue domain entity or None if conversion failed
        """
        try:
            # Convert date string to date object
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Extract factor value from IBKR data
            ibkr_data = {
                'contract': contract,
                'contract_details': contract_details
            }
            
            factor_value_string = self._extract_value_for_factor(factor_id, ibkr_data)
            
            if factor_value_string is None:
                print(f"Could not extract factor value for factor {factor_id} from IBKR data")
                return None
            
            # Create FactorValue domain entity
            return FactorValue(
                id=None,  # Let database generate
                factor_id=factor_id,
                entity_id=entity_id,
                date=date_obj,
                value=factor_value_string
            )
        except Exception as e:
            print(f"Error converting IBKR contract to factor value: {e}")
            return None

    def _extract_value_for_factor(self, factor_id: int, ibkr_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract specific factor value from IBKR contract data based on factor ID.
        
        Args:
            factor_id: The factor ID to extract
            ibkr_data: Raw IBKR data dictionary containing contract and contract_details
            
        Returns:
            Factor value as string or None if not available
        """
        try:
            contract = ibkr_data.get('contract')
            contract_details = ibkr_data.get('contract_details')
            
            if not contract or not contract_details:
                return None

            # Map factor IDs to IBKR contract fields
            # This mapping would be based on your factor definitions
            factor_mapping = {
                1: contract.symbol,  # Symbol
                2: getattr(contract_details, 'longName', ''),  # Company long name
                3: getattr(contract_details, 'industry', ''),  # Industry
                4: getattr(contract_details, 'category', ''),  # Category
                5: str(getattr(contract_details, 'minTick', 0)),  # Minimum tick size
                6: contract.currency,  # Currency
                7: contract.exchange,  # Exchange
                # Add more mappings as needed based on your factor definitions
            }
            
            value = factor_mapping.get(factor_id)
            if value is None or value == '':
                # If no direct mapping, try to get from contract details attributes
                value = str(getattr(contract_details, f'factor_{factor_id}', ''))
            
            return value if value else None
            
        except Exception as e:
            print(f"Error extracting factor value {factor_id} from IBKR data: {e}")
            return None