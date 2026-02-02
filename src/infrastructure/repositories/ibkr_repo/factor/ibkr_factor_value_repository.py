"""
IBKR Factor Value Repository - Interactive Brokers implementation for FactorValue entities.

This repository handles factor value data acquisition from IBKR API,
implementing the pipelines for IBKR Contract → Instrument → Factor Values → Asset Factor Values.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
import inspect
from ibapi.contract import Contract
from domain.entities.finance.financial_assets.currency import Currency

from src.infrastructure.repositories.ibkr_repo.factor.ibkr_instrument_factor_repository import IBKRInstrumentFactorRepository
from src.domain.ports.factor.factor_value_port import FactorValuePort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.factor import Factor
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
         factory =None,
        ibkr_instrument_repo: Optional['IBKRInstrumentRepository'] = None
    ):
        """
        Initialize IBKR Factor Value Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            factory: Factory for accessing other repositories
            ibkr_instrument_repo: IBKR instrument repository for contract→instrument flow
        """
        super().__init__(ibkr_client)
        self.ibkr_instrument_repo = ibkr_instrument_repo
        self.factory = factory
        self.ibkr_instrument_factor_repo = self.factory.instrument_factor_ibkr_repo
        self.tick_mapper = IBKRTickFactorMapper()
        
    @property 
    def local_repo(self):
        """Get local factor value repository through factory."""
        if hasattr(self, '_local_repo') and self._local_repo:
            return self._local_repo
        if self.factory:
            return self.factory.factor_value_local_repo
        return None

    # Pipeline Methods - Main functionality requested by user
    @property
    def entity_class(self):
        return FactorValue
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
            
            # 6. Use factory to get ibkr_instrument_factor_repository and call get_or_create
            if self.factory:
                instrument_factor_repo = self.factory.instrument_factor_ibkr_repo
                if instrument_factor_repo:
                    # Get the factor entity from local repository
                    factor_repo = self.factory.factor_local_repo
                    if factor_repo:
                        factor_entity = factor_repo.get_by_id(factor_id)
                        if factor_entity:
                            # Get financial asset entity - this should be passed from caller
                            financial_asset_entity = self.factory.financial_asset_local_repo.get_by_id(entity_id)
                            if financial_asset_entity:
                                # Call get_or_create on instrument factor repository to create factor value
                                # for the proper financial asset entity and factor entity
                                factor_value = self._create_or_get(
                                    entity_symbol=symbol_or_name,  # Pass the symbol
                                    factor=factor_entity,
                                    entity=financial_asset_entity,
                                    date=time,
                                    instrument=instrument,
                                    tick_data=tick_data
                                )
                                return factor_value
            
            # 7. Fallback: retrieve the specific factor value requested
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

    def _create_or_get(
        self,
         entity_symbol,
        **kwargs
    ) -> Optional[FactorValue]:
        """
        Enhanced get_or_create function with automatic dependency resolution and IBKR API integration.
        
        This method implements the functionality described in the issue:
        1. Takes factor entity, financial asset entity, date, and kwargs
        2. If no dependencies: directly fetch factor value from IBKR (e.g., open price)
        3. If dependencies: get other factor values from IBKR, populate in DB, use calculate function
        4. Stores the result in the database
        
        Args:
            factor_entity: Factor domain entity instance
            financial_asset_entity: Financial asset entity (company share, etc)  
            time_date: Date string in 'YYYY-MM-DD' format
            **kwargs: Additional parameters for factor calculation
            
        Returns:
            FactorValue entity or None if creation/retrieval failed
        """
        try:
            factor_entity = kwargs.get('factor')
            financial_asset_entity = kwargs.get('entity')
            time_date = kwargs.get('date')
            if not factor_entity or not financial_asset_entity:
                print("Factor entity and financial asset entity are required")
                return None

            # Ensure time_date is a string
            if isinstance(time_date, date):
                time_date = time_date.strftime("%Y-%m-%d")
            elif not isinstance(time_date, str):
                time_date = str(time_date)
            
            # Parse date object for storage
            date_obj = datetime.strptime(time_date, "%Y-%m-%d").date()

            # Get entity ID from financial asset (assumes entity has 'id' attribute)
            entity_id = getattr(financial_asset_entity, 'id')
            factor_id = factor_entity.id
            
            # 1. Check if factor value already exists for this combination
            existing = self._check_existing_factor_value(factor_id, entity_id, time_date)
            if existing:
                return existing
            
            # 2. Get factor dependencies from the factor class definition
            dependencies = self._get_factor_dependencies(factor_entity)
            
            if dependencies:
                # CASE 1: Factor has dependencies - resolve dependencies first, then calculate
                print(f"Factor {factor_entity.name} has dependencies: {list(dependencies.keys())}")
                
                # 3. Resolve all dependencies recursively from IBKR
                resolved_dependencies = {}
                for dep_name, dep_factor_info in dependencies.items():
                    dep_value = self._resolve_factor_dependency_from_ibkr(
                        dep_factor_info,
                        financial_asset_entity,
                        time_date,
                        **kwargs
                    )
                    if dep_value is not None:
                        resolved_dependencies[dep_name] = dep_value
                    else:
                        print(f"Warning: Could not resolve dependency {dep_name} for factor {factor_entity.name}")
                
                # 4. Call the factor's calculate method with resolved dependencies
                calculated_value = self._call_factor_calculate_method(
                    factor_entity,
                    financial_asset_entity,
                    resolved_dependencies,
                    **kwargs
                )
                
                if calculated_value is None:
                    print(f"Factor calculation failed for {factor_entity.name}")
                    return None
            
                # 5. Create and store the factor value
                factor_value = FactorValue(
                    id=None,  # Let database generate
                    factor_id=factor_id,
                    entity_id=entity_id,
                    date=date_obj,
                    value=str(calculated_value)  # Convert to string for storage
                )
                
            else:
                # CASE 2: No dependencies - fetch directly from IBKR
                print(f"Factor {factor_entity.name} has no dependencies - fetching directly from IBKR")
                
                
                    
                # Use the new pattern with ibkr_instrument_repo.get_or_create_from_contract
                contract = self._fetch_contract(factor_entity, financial_asset_entity)
                if not contract:
                    return None
                    
                contract_details_list = self._fetch_contract_details(contract)
                if not contract_details_list:
                    return None
                
                # Use the instrument repository pattern to get factor value
                timestamp = datetime.now()  # Use current timestamp for IBKR data
                # Check if ibkr_instrument_repo is available
                self.ibkr_instrument_repo = self.factory.instrument_ibkr_repo
                instrument = self.ibkr_instrument_repo.get_or_create_from_contract(
                    contract=contract,
                    contract_details=contract_details_list,
                    tick_data=None,  # No specific tick data for basic factor values
                    timestamp=timestamp
                )
                
                if not instrument:
                    print(f"Failed to create instrument for factor {factor_entity.name}")
                    return None
                factor_value = self.factory.instrument_factor_ibkr_repo.get_or_create(instrument=instrument,contract = contract, factor= factor_entity,entity= financial_asset_entity)
               
                return factor_value
        except Exception as e:
            print(f"Error in get_or_create_factor_value_with_dependencies for {factor_entity.name}: {e}")
            return None

    def _get_factor_dependencies(self, factor_entity: Factor) -> Dict[str, Dict[str, Any]]:
        """
        Extract dependencies from factor class definition.
        
        Looks for:
        1. Class attribute 'dependencies' 
        2. Method parameters that might indicate dependencies
        3. Factor-specific dependency patterns
        
        Args:
            factor_entity: Factor domain entity
            
        Returns:
            Dict mapping dependency names to dependency information
        """
        dependencies = {}
        
        try:
            factor_class = factor_entity.__class__
            
            # 1. Check for explicit dependencies attribute
            if hasattr(factor_class, 'dependencies'):
                deps = getattr(factor_class, 'dependencies')
                if isinstance(deps, dict):
                    dependencies.update(deps)
                elif isinstance(deps, list):
                    # Convert list to dict with basic info
                    for dep in deps:
                        dependencies[dep] = {'name': dep, 'required': True}
            
                # 2. Analyze calculate method parameters
                calculate_methods = [method for method in dir(factor_class) 
                                if method.startswith('calculate') and callable(getattr(factor_class, method))]
                
                for method_name in calculate_methods:
                    method = getattr(factor_class, method_name)
                    if hasattr(method, '__code__'):
                        # Get method parameter names (excluding 'self')
                        param_names = method.__code__.co_varnames[1:method.__code__.co_argcount]
                        for param in param_names:
                            if param not in dependencies and param not in ['time_date', 'kwargs', 'params']:
                                # Infer dependency type from parameter name
                                dependencies[param] = {
                                    'name': param,
                                    'required': True,
                                    'method': method_name
                                }
            
            
        
        except Exception as e:
            print(f"Error extracting dependencies for {factor_entity.name}: {e}")
        
        return dependencies

    def _resolve_factor_dependency_from_ibkr(
        self,
        dep_info: Dict[str, Any],
        financial_asset_entity: Any,
        time_date: str,
        **kwargs
    ) -> Optional[Any]:
        """
        Resolve a single factor dependency by fetching from IBKR and populating in DB.
        
        Args:
            dep_info: Dependency information dictionary
            financial_asset_entity: Financial asset entity
            time_date: Date string
            **kwargs: Additional parameters
            
        Returns:
            Resolved dependency value or None
        """
        try:
            dep_name = dep_info.get('name')
            
            # Check if dependency is provided in kwargs first
            if dep_name in kwargs:
                return kwargs[dep_name]
            
            # Special handling for common dependencies - fetch from IBKR and store in DB
            if self.factory:
                if dep_name == 'price_data':
                    return self._get_or_create_price_data_from_ibkr(financial_asset_entity, time_date)
                elif dep_name == 'volume_data':
                    return self._get_or_create_volume_data_from_ibkr(financial_asset_entity, time_date)
                elif dep_name == 'underlying_price':
                    return self._get_or_create_underlying_price_from_ibkr(financial_asset_entity, time_date)
                elif dep_name == 'volatility':
                    return self._get_or_create_volatility_data_from_ibkr(financial_asset_entity, time_date)
                elif dep_name == 'risk_free_rate':
                    return self._get_or_create_risk_free_rate_from_ibkr(time_date)
                else:
                    # Try to resolve as another factor value from IBKR
                    return self._resolve_factor_value_dependency_from_ibkr(dep_name, financial_asset_entity, time_date)
            
            return None
            
        except Exception as e:
            print(f"Error resolving dependency {dep_info.get('name', 'unknown')} from IBKR: {e}")
            return None

    def _resolve_factor_dependency(
        self,
        dep_info: Dict[str, Any],
        financial_asset_entity: Any,
        time_date: str,
        **kwargs
    ) -> Optional[Any]:
        """
        Resolve a single factor dependency.
        
        Args:
            dep_info: Dependency information dictionary
            financial_asset_entity: Financial asset entity
            time_date: Date string
            **kwargs: Additional parameters
            
        Returns:
            Resolved dependency value or None
        """
        try:
            dep_name = dep_info.get('name')
            
            # Check if dependency is provided in kwargs
            if dep_name in kwargs:
                return kwargs[dep_name]
            
            # Try to resolve from factory repositories
            if self.factory:
                
                # Special handling for common dependencies
                if dep_name == 'price_data':
                    # Try to get price data from market data or other sources
                    return self._get_price_data(financial_asset_entity, time_date)
                    
                elif dep_name == 'volume_data':
                    return self._get_volume_data(financial_asset_entity, time_date)
                    
                elif dep_name == 'underlying_price':
                    return self._get_underlying_price(financial_asset_entity, time_date)
                    
                elif dep_name == 'volatility':
                    return self._get_volatility_data(financial_asset_entity, time_date)
                    
                elif dep_name == 'risk_free_rate':
                    return self._get_risk_free_rate(time_date)
                    
                else:
                    # Try to resolve as another factor value
                    return self._resolve_factor_value_dependency(dep_name, financial_asset_entity, time_date)
            
            return None
            
        except Exception as e:
            print(f"Error resolving dependency {dep_info.get('name', 'unknown')}: {e}")
            return None

    def _call_factor_calculate_method(
        self,
        factor_entity: Factor,
        financial_asset_entity: Any,
        resolved_dependencies: Dict[str, Any],
        **kwargs
    ) -> Optional[Any]:
        """
        Call the appropriate calculate method on the factor with resolved dependencies.
        
        Args:
            factor_entity: Factor domain entity
            financial_asset_entity: Financial asset entity
            resolved_dependencies: Dict of resolved dependency values
            **kwargs: Additional parameters
            
        Returns:
            Calculated factor value or None
        """
        try:
            factor_class = factor_entity.__class__
            
            # Look for calculate methods in order of preference
            calculate_methods = [
                'calculate',
                'calculate_momentum',
                'calculate_price', 
                'calculate_value',
                'compute'
            ]
            
            for method_name in calculate_methods:
                if hasattr(factor_class, method_name):
                    method = getattr(factor_entity, method_name)
                    if callable(method):
                        
                        # Try to call the method with resolved dependencies
                        try:
                            # Get method signature to match parameters
                            sig = inspect.signature(method)
                            method_params = {}
                            
                            for param_name, param in sig.parameters.items():
                                if param_name in resolved_dependencies:
                                    method_params[param_name] = resolved_dependencies[param_name]
                                elif param_name in kwargs:
                                    method_params[param_name] = kwargs[param_name]
                            
                            # Call the method
                            result = method(**method_params)
                            if result is not None:
                                return result
                                
                        except Exception as method_error:
                            print(f"Error calling {method_name} on {factor_entity.name}: {method_error}")
                            continue
            
            print(f"No suitable calculate method found for {factor_entity.name}")
            return None
            
        except Exception as e:
            print(f"Error calling factor calculate method for {factor_entity.name}: {e}")
            return None


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

    def _validate_factor_value_data(self, factor_id: int, entity_id: int, time_date: str) -> bool:
        """
        Validate factor value data before processing.
        
        Args:
            factor_id: Factor ID
            entity_id: Entity ID  
            time_date: Date string in 'YYYY-MM-DD' format
            
        Returns:
            True if data is valid, False otherwise
        """
        try:
            if not factor_id or factor_id <= 0:
                print(f"Invalid factor_id: {factor_id}")
                return False
            
            if not entity_id or entity_id <= 0:
                print(f"Invalid entity_id: {entity_id}")
                return False
            
            if not time_date:
                print("Time date is required")
                return False
                
            # Validate date format
            try:
                datetime.strptime(time_date, '%Y-%m-%d')
            except ValueError:
                print(f"Invalid date format: {time_date}. Expected YYYY-MM-DD")
                return False
            
            return True
            
        except Exception as e:
            print(f"Error validating factor value data: {e}")
            return False

    def _check_existing_factor_value(self, factor_id: int, entity_id: int, time_date: str) -> Optional[FactorValue]:
        """
        Check if factor value already exists for the given combination.
        
        Args:
            factor_id: Factor ID
            entity_id: Entity ID
            time_date: Date string in 'YYYY-MM-DD' format
            
        Returns:
            Existing FactorValue or None
        """
        try:
            # Try local repository first
            if hasattr(self, 'local_repo') and self.local_repo:
                return self.local_repo.get_by_factor_entity_date(factor_id, entity_id, time_date)
            
           
            
        except Exception as e:
            print(f"Error checking existing factor value: {e}")
            return None

    def _fetch_contract(self, factor_entity: Factor, financial_asset_entity: Any) -> Optional['Contract']:
        """
        Fetch IBKR contract for factor entity and financial asset entity.
        
        Args:
            factor_entity: Factor domain entity
            financial_asset_entity: Financial asset entity (company share, etc)
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            # --- Extract symbol ---
            symbol = (
                getattr(financial_asset_entity, 'symbol', None)
                or getattr(financial_asset_entity, 'ticker', None)
                or getattr(financial_asset_entity, 'name', None)
            )

            if not symbol:
                print(f"Could not extract symbol from financial asset entity {financial_asset_entity}")
                return None

            contract = Contract()
            contract.symbol = symbol.upper()

            # --- secType routing ---
            if isinstance(financial_asset_entity, self.factory.index_local_repo.entity_class):
                contract.secType = "IND"
                contract.exchange = "CBOE"   # or SMART, see note below
            else:
                contract.secType = "STK"
                contract.exchange = "SMART"
                contract.primaryExchange = "NASDAQ"  # optional but recommended

            # --- currency ---
            currency = self.factory.currency_local_repo.get_by_id(
                getattr(financial_asset_entity, 'currency_id', None)
            )
            contract.currency = currency.symbol if currency else "USD"

            return contract
                
        except Exception as e:
            print(f"Error fetching IBKR contract for factor {factor_entity.name}: {e}")
            return None

    def _fetch_contract_for_symbol(self, symbol_or_name: str) -> Optional['Contract']:
        """
        Fetch IBKR contract for symbol or name.
        
        Args:
            symbol_or_name: Stock symbol or asset name
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            
            
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

    def _contract_to_domain(
        self, 
        contract: 'Contract', 
        contract_details_list: Any,
        factor_entity: Factor,
        financial_asset_entity: Any,
        date_obj: date
    ) -> Optional[FactorValue]:
        """
        Convert IBKR contract and details to a FactorValue domain entity.
        
        Args:
            contract: IBKR Contract object
            contract_details_list: IBKR ContractDetails object or list
            factor_entity: Factor entity requesting the value
            financial_asset_entity: Financial asset entity
            date_obj: Date object for the factor value
            
        Returns:
            FactorValue domain entity or None if conversion failed
        """
        try:
            # Get IDs
            factor_id = factor_entity.id
            entity_id = getattr(financial_asset_entity, 'id')
            
            # Extract factor value from IBKR data
            ibkr_data = {
                'contract': contract,
                'contract_details': contract_details_list
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