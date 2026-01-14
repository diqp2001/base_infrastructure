"""
IBKR Company Share Repository - Interactive Brokers implementation for Company Shares.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.domain.ports.factor.factor_value_port import FactorValuePort
from src.domain.ports.finance.financial_assets.share.company_share.company_share_port import CompanySharePort
from src.domain.ports.finance.instrument_port import InstrumentPort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.finance.instrument.ibkr_instrument import IBKRInstrument

from ...tick_types.ibkr_tick_mapping import IBKRTickType

# Forward reference for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..instrument_repository import IBKRInstrumentRepository


class IBKRCompanyShareRepository(IBKRFinancialAssetRepository, CompanySharePort):
    """
    IBKR implementation of CompanySharePort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(
        self, 
        ibkr_client, 
        local_repo: CompanySharePort, 
        local_factor_value_repo: FactorValuePort,
        ibkr_instrument_repo: Optional['IBKRInstrumentRepository'] = None
    ):
        """
        Initialize IBKR Company Share Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            local_repo: Local repository implementing CompanySharePort for persistence
            local_factor_value_repo: Local repository for factor value persistence
            ibkr_instrument_repo: IBKR instrument repository for contract handling (optional)
        """
        super().__init__(ibkr_client)
        self.local_repo = local_repo
        self.local_factor_value_repo = local_factor_value_repo
        self.ibkr_instrument_repo = ibkr_instrument_repo

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
        1. Create IBKR Contract → Instrument
        2. Extract tick data → Factor Values 
        3. Map Instrument Factor Values → Company Share Factor Values
        
        Args:
            symbol_or_name: Stock symbol or company name
            factor_id: The factor ID (integer)
            time: Date string in 'YYYY-MM-DD' format
            tick_data: Optional IBKR tick data dictionary (tick_type_id -> value)
            
        Returns:
            FactorValue entity or None if creation/retrieval failed
        """
        try:
            if not self.ibkr_instrument_repo:
                print("IBKR instrument repository not available, falling back to legacy method")
                return self.get_or_create_factor_value(symbol_or_name, factor_id, time)
            
            # 1. Get or create company share entity first
            company_share = self.get_or_create(symbol_or_name)
            if not company_share:
                print(f"Could not find or create company share for {symbol_or_name}")
                return None
            
            # 2. Check if factor value already exists for this date
            list_of_dates = self.local_factor_value_repo.get_all_dates_by_id_entity_id(factor_id, company_share.id)
            if time in list_of_dates:
                # Return existing factor value
                existing = self.local_factor_value_repo.get_by_factor_entity_date(factor_id, company_share.id, time)
                return existing
            
            # 3. Fetch IBKR contract
            contract = self._fetch_stock_contract(symbol_or_name)
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
            return self.local_factor_value_repo.get_by_factor_entity_date(
                factor_id, company_share.id, time
            )
            
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
            
            # Use instrument-based method with tick data
            return self.get_or_create_factor_value_with_ticks(
                symbol_or_name=symbol,
                factor_id=None,  # Will be resolved from tick mapping
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
            # 1. Get or create company share entity first
            company_share = self.get_or_create(symbol_or_name)
            if not company_share:
                print(f"Could not find or create company share for {symbol_or_name}")
                return None
            
            # 2. Check if factor value already exists for this date
            list_of_dates = self.local_factor_value_repo.get_all_dates_by_id_entity_id(factor_id, company_share.id)
            if time in list_of_dates:
                # Return existing factor value
                existing = self.local_factor_value_repo.get_by_factor_entity_date(factor_id, company_share.id, time)
                return existing
            
            # 3. Fetch company info via stock contract from IBKR API
            contract = self._fetch_stock_contract(symbol_or_name)
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
            return self.local_factor_value_repo.add(factor_value)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create_factor_value for company {symbol_or_name}: {e}")
            return None
        
    def _fetch_stock_contract(self, symbol_or_name: str) -> Optional[Contract]:
        """
        Fetch stock contract to get company information.
        
        Args:
            symbol_or_name: Stock symbol or company name
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            # Try as symbol first
            if len(symbol_or_name) <= 5 and symbol_or_name.isupper():
                contract.symbol = symbol_or_name
            else:
                # If it looks like a company name, we'd need different approach
                # For now, assume it's a symbol
                contract.symbol = symbol_or_name.upper()
            
            contract.secType = "STK"
            contract.exchange = "SMART"
            contract.currency = "USD"
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR stock contract for {symbol_or_name}: {e}")
            return None


    def get_or_create(self, symbol: str) -> Optional[CompanyShare]:
        """
        Get or create a company share by symbol using IBKR API.
        
        Args:
            symbol: The stock ticker symbol (e.g., 'AAPL', 'MSFT')
            
        Returns:
            CompanyShare entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            existing = self.local_repo.get_by_ticker(symbol)
            if existing:
                return existing[0] if isinstance(existing, list) else existing
            
            # 2. Fetch from IBKR API
            contract = self._fetch_contract(symbol)
            if not contract:
                return None
                
            # 3. Get contract details from IBKR
            contract_details = self._fetch_contract_details(contract)
            if not contract_details:
                return None
                
            # 4. Apply IBKR-specific rules and convert to domain entity
            entity = self._contract_to_domain(contract, contract_details)
            if not entity:
                return None
                
            # 5. Delegate persistence to local repository
            return self.local_repo.add(entity)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for symbol {symbol}: {e}")
            return None

    def get_by_ticker(self, ticker: str) -> List[CompanyShare]:
        """Get company share by ticker (delegates to local repository)."""
        return self.local_repo.get_by_ticker(ticker)

    def get_by_id(self, entity_id: int) -> Optional[CompanyShare]:
        """Get company share by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[CompanyShare]:
        """Get all company shares (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: CompanyShare) -> Optional[CompanyShare]:
        """Add company share entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity_id: int, **kwargs) -> Optional[CompanyShare]:
        """Update company share entity (delegates to local repository)."""
        return self.local_repo.update(entity_id, **kwargs)

    def delete(self, entity_id: int) -> bool:
        """Delete company share entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def exists_by_ticker(self, ticker: str) -> bool:
        """Check if company share exists by ticker (delegates to local repository)."""
        return self.local_repo.exists_by_ticker(ticker)

    def get_by_company_id(self, company_id: int) -> List[CompanyShare]:
        """Get company shares by company ID (delegates to local repository)."""
        return self.local_repo.get_by_company_id(company_id)

    def _fetch_contract(self, symbol: str) -> Optional[Contract]:
        """
        Fetch contract from IBKR API.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            contract.symbol = symbol.upper()
            contract.secType = "STK"
            contract.exchange = "SMART"  # IBKR smart routing
            contract.currency = "USD"
            
            # Apply IBKR-specific contract setup
            contract = self._apply_ibkr_symbol_rules(contract, symbol)
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR contract for {symbol}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[ContractDetails]:
        """
        Fetch contract details from IBKR API.
        
        Args:
            contract: IBKR Contract object
            
        Returns:
            ContractDetails object or None if not found
        """
        try:
            # This would involve an actual IBKR API call
            # For now, return a mock object to demonstrate the pattern
            # In real implementation, use self.ibkr.reqContractDetails()
            
            contract_details = ContractDetails()
            contract_details.contract = contract
            # Set additional details that come from IBKR
            contract_details.marketName = "Stock Market"
            contract_details.minTick = 0.01  # Typical for stocks
            contract_details.priceMagnifier = 1
            contract_details.orderTypes = "LMT,MKT,STP,TRAIL"
            contract_details.longName = f"{contract.symbol} Inc."
            contract_details.industry = "Technology"
            contract_details.category = "Common Stock"
            
            return contract_details
        except Exception as e:
            print(f"Error fetching IBKR contract details: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details: ContractDetails) -> Optional[CompanyShare]:
        """
        Convert IBKR contract and details directly to domain entity.
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object
            
        Returns:
            CompanyShare domain entity or None if conversion failed
        """
        try:
            # Apply IBKR-specific business rules and create domain entity
            return CompanyShare(
                id=None,  # Let database generate
                ticker=contract.symbol,
                exchange_id=self._resolve_exchange_id(contract.exchange, contract_details),
                company_id=self._resolve_company_id(contract.symbol, contract_details),
                start_date=None,  # Will be set based on IBKR data
                end_date=None,    # Active securities don't have end dates
                # Additional IBKR-specific fields can be stored as metadata
                ibkr_contract_id=getattr(contract, 'conId', None),
                ibkr_local_symbol=getattr(contract, 'localSymbol', ''),
                ibkr_trading_class=getattr(contract, 'tradingClass', ''),
                ibkr_long_name=getattr(contract_details, 'longName', ''),
                ibkr_industry=getattr(contract_details, 'industry', ''),
                ibkr_category=getattr(contract_details, 'category', '')
            )
        except Exception as e:
            print(f"Error converting IBKR contract to domain entity: {e}")
            return None

    def _apply_ibkr_symbol_rules(self, contract: Contract, original_symbol: str) -> Contract:
        """Apply IBKR-specific symbol resolution and exchange rules."""
        # Handle special cases for IBKR
        symbol = original_symbol.upper()
        
        # Map common symbols to IBKR equivalents
        ibkr_symbol_map = {
            'BRK.A': 'BRK A',  # Berkshire Hathaway Class A
            'BRK.B': 'BRK B',  # Berkshire Hathaway Class B
        }
        
        contract.symbol = ibkr_symbol_map.get(symbol, symbol)
        
        # Set appropriate exchange based on symbol patterns
        if symbol.endswith('.TO'):  # Toronto Stock Exchange
            contract.exchange = 'TSE'
            contract.currency = 'CAD'
            contract.symbol = symbol[:-3]  # Remove .TO suffix
        elif symbol.endswith('.L'):  # London Stock Exchange
            contract.exchange = 'LSE'
            contract.currency = 'GBP'
            contract.symbol = symbol[:-2]  # Remove .L suffix
        elif any(symbol.startswith(prefix) for prefix in ['NYSE:', 'NASDAQ:']):
            # Remove exchange prefix if present
            contract.symbol = symbol.split(':', 1)[1]
            
        return contract

    def _resolve_exchange_id(self, ibkr_exchange: str, contract_details: ContractDetails) -> int:
        """Resolve exchange ID from IBKR exchange code."""
        # This would typically involve looking up or creating exchange entities
        # For now, return default values
        exchange_map = {
            'SMART': 1,    # Default
            'NASDAQ': 2,   # NASDAQ
            'NYSE': 3,     # NYSE
            'TSE': 4,      # Toronto
            'LSE': 5,      # London
        }
        return exchange_map.get(ibkr_exchange, 1)

    def _resolve_company_id(self, symbol: str, contract_details: ContractDetails) -> int:
        """Resolve company ID from IBKR data."""
        # This would typically involve looking up or creating company entities
        # For now, return a default value
        # In real implementation, you'd create/lookup the company based on
        # contract_details.longName, industry, etc.
        return 1
    
    def _contract_to_factor_value(self, contract: Contract, contract_details: ContractDetails, 
                                  factor_id: int, entity_id: int, date_str: str) -> Optional[FactorValue]:
        """
        Convert IBKR contract and details to a FactorValue domain entity.
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object
            factor_id: The factor ID
            entity_id: The entity (company share) ID
            date_str: Date string in 'YYYY-MM-DD' format
            
        Returns:
            FactorValue domain entity or None if conversion failed
        """
        try:
            # Convert date string to date object
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Extract factor value from IBKR data
            # This is where you'd apply IBKR-specific business rules to extract
            # the relevant factor value from the contract details
            factor_value_string = self._extract_factor_value_from_contract(contract, contract_details, factor_id)
            
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
    
    def _extract_factor_value_from_contract(self, contract: Contract, contract_details: ContractDetails, 
                                           factor_id: int) -> Optional[str]:
        """
        Extract specific factor value from IBKR contract data based on factor ID.
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object
            factor_id: The factor ID to extract
            
        Returns:
            Factor value as string or None if not available
        """
        try:
            # Map factor IDs to IBKR contract fields
            # This mapping would be based on your factor definitions
            factor_mapping = {
                1: contract.symbol,  # Company ticker symbol
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
                # This allows for dynamic factor extraction
                value = str(getattr(contract_details, f'factor_{factor_id}', ''))
            
            return value if value else None
            
        except Exception as e:
            print(f"Error extracting factor value {factor_id} from IBKR data: {e}")
            return None