"""
IBKR Company Share Factor Repository - Interactive Brokers implementation for Company Share factors.

This repository integrates with IBKRCompanyShareRepository to provide factor-specific operations
for company shares using IBKR data.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date

from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository
from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.infrastructure.repositories.ibkr_repo.tick_types.ibkr_tick_mapping import IBKRTickType

# Forward references for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.company_share_repository import IBKRCompanyShareRepository
    from src.domain.ports.finance.financial_assets.share.company_share.company_share_port import CompanySharePort


class IBKRCompanyShareFactorRepository(IBKRFactorValueRepository):
    """
    IBKR Company Share Factor Repository.
    
    Specialized factor value repository that works with IBKRCompanyShareRepository
    to implement the complete pipeline:
    1. IBKR Contract → Company Share
    2. IBKR Contract → Instrument
    3. Tick Data → Factor Values
    4. Map to Company Share Factor Values
    """

    def __init__(
        self, 
        ibkr_client, 
        local_factor_value_repo,
        company_share_repo: 'IBKRCompanyShareRepository'
    ):
        """
        Initialize IBKR Company Share Factor Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            local_factor_value_repo: Local repository for factor value persistence
            company_share_repo: IBKR company share repository for entity resolution
        """
        super().__init__(ibkr_client, local_factor_value_repo)
        self.company_share_repo = company_share_repo

    def get_or_create_factor_value_with_ticks(
        self, 
        symbol_or_name: str, 
        factor_id: int, 
        time: str,
        tick_data: Optional[Dict[int, Any]] = None
    ) -> Optional[FactorValue]:
        """
        Get or create a factor value for a company by symbol using IBKR API with instrument flow.
        
        This method follows the new architecture:
        1. Create IBKR Contract → Company Share
        2. Create IBKR Contract → Instrument
        3. Extract tick data → Factor Values 
        4. Map Instrument Factor Values → Company Share Factor Values
        
        Args:
            symbol_or_name: Stock symbol or company name
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
            
            # 1. Get or create company share entity first
            company_share = self.company_share_repo.get_or_create(symbol_or_name)
            if not company_share:
                print(f"Could not find or create company share for {symbol_or_name}")
                return None
            
            # 2. Check if factor value already exists for this date
            existing = self._check_existing_factor_value(factor_id, company_share.id, time)
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
            # and maps them to the financial asset (company share)
            # So we just need to retrieve the specific factor value requested
            return self._check_existing_factor_value(factor_id, company_share.id, time)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create_factor_value_with_ticks for company {symbol_or_name}: {e}")
            return None
    
    def create_factor_value_from_tick_data(
        self,
        symbol: str,
        tick_type: IBKRTickType,
        tick_value: Any,
        time: str
    ) -> Optional[FactorValue]:
        """
        Create a factor value from specific IBKR tick data for a company share.
        
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
        Get or create a factor value for a company by symbol or name using IBKR API.
        
        Args:
            symbol_or_name: Stock symbol or company name
            factor_id: The factor ID (integer)
            time: Date string in 'YYYY-MM-DD' format
            
        Returns:
            FactorValue entity or None if creation/retrieval failed
        """
        try:
            if not self._validate_factor_value_data(factor_id, 1, time):  # Entity ID validated later
                return None
                
            # 1. Get or create company share entity first
            company_share = self.company_share_repo.get_or_create(symbol_or_name)
            if not company_share:
                print(f"Could not find or create company share for {symbol_or_name}")
                return None
            
            # 2. Check if factor value already exists for this date
            existing = self._check_existing_factor_value(factor_id, company_share.id, time)
            if existing:
                return existing
            
            # 3. Fetch company info via stock contract from IBKR API
            contract = self._fetch_contract_for_symbol(symbol_or_name)
            if not contract:
                return None
                
            # 4. Get contract details from IBKR
            contract_details = self._fetch_contract_details(contract)
            if not contract_details:
                return None
                
            # 5. Apply IBKR-specific rules and convert to factor value
            factor_value = self._contract_to_factor_value(contract, contract_details, factor_id, company_share.id, time)
            if not factor_value:
                return None
                
            # 6. Delegate persistence to local repository
            return self.local_repo.add(factor_value)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create_factor_value for company {symbol_or_name}: {e}")
            return None

    def get_company_share_factors_by_symbol(self, symbol: str) -> List[FactorValue]:
        """
        Get all factor values for a company share by symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of FactorValue entities for the company share
        """
        try:
            # Get the company share entity
            company_share = self.company_share_repo.get_or_create(symbol)
            if not company_share:
                return []
            
            # Get all factor values for this entity
            return self.local_repo.get_by_entity_id(company_share.id)
            
        except Exception as e:
            print(f"Error getting company share factors for {symbol}: {e}")
            return []

    def get_company_share_factor_time_series(
        self, 
        symbol: str, 
        factor_id: int, 
        start_date: date, 
        end_date: date
    ) -> List[FactorValue]:
        """
        Get time series data for a specific factor of a company share.
        
        Args:
            symbol: Stock symbol
            factor_id: The factor ID
            start_date: Start date
            end_date: End date
            
        Returns:
            List of FactorValue entities for the time series
        """
        try:
            # Get the company share entity
            company_share = self.company_share_repo.get_or_create(symbol)
            if not company_share:
                return []
            
            # Get time series data
            return self.local_repo.get_time_series(factor_id, company_share.id, start_date, end_date)
            
        except Exception as e:
            print(f"Error getting time series for {symbol}, factor {factor_id}: {e}")
            return []

    def _check_existing_factor_value(self, factor_id: int, entity_id: int, time: str) -> Optional[FactorValue]:
        """
        Override to use the local repository directly for company share factor values.
        
        Args:
            factor_id: The factor ID
            entity_id: The company share entity ID
            time: Date string in 'YYYY-MM-DD' format
            
        Returns:
            Existing FactorValue or None if not found
        """
        try:
            return self.local_repo.get_by_factor_entity_date(factor_id, entity_id, time)
        except Exception as e:
            print(f"Error checking existing factor value: {e}")
            return None