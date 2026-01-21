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

from src.domain.ports.finance.financial_assets.share.company_share.company_share_port import CompanySharePort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare

# Forward reference for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_company_share_factor_repository import IBKRCompanyShareFactorRepository


class IBKRCompanyShareRepository(IBKRFinancialAssetRepository, CompanySharePort):
    """
    IBKR implementation of CompanySharePort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory):
        """
        Initialize IBKR Company Share Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client (InteractiveBrokersBroker instance)
            factory: Repository factory for dependency injection (preferred)
        """
        self.ib_broker = ibkr_client  # Use ib_broker for consistency with reference implementation
        
        self.factory = factory
        self.local_repo = self.factory.company_share_local_repo

    @property
    def entity_class(self):
        """Return the domain entity class for CompanyShare."""
        return CompanyShare

    # Factor-related methods (delegated to factor repository)
    
    def get_or_create_factor_value_with_ticks(
        self, 
        symbol_or_name: str, 
        factor_id: int, 
        time: str,
        tick_data: Optional[Dict[int, Any]] = None
    ):
        """
        Get or create a factor value using the specialized factor repository.
        
        This method is now delegated to IBKRCompanyShareFactorRepository.
        """
        if not self.factor_repo:
            print("Factor repository not available")
            return None
        return self.factor_repo.get_or_create_factor_value_with_ticks(
            symbol_or_name, factor_id, time, tick_data
        )
    
    def create_factor_value_from_tick_data(self, symbol: str, tick_type, tick_value: Any, time: str):
        """
        Create a factor value from tick data using the specialized factor repository.
        
        This method is now delegated to IBKRCompanyShareFactorRepository.
        """
        if not self.factor_repo:
            print("Factor repository not available")
            return None
        return self.factor_repo.create_factor_value_from_tick_data(
            symbol, tick_type, tick_value, time
        )

    def get_or_create_factor_value(self, symbol_or_name: str, factor_id: int, time: str):
        """
        Get or create a factor value using the specialized factor repository.
        
        This method is now delegated to IBKRCompanyShareFactorRepository.
        """
        if not self.factor_repo:
            print("Factor repository not available")
            return None
        return self.factor_repo.get_or_create_factor_value(symbol_or_name, factor_id, time)
        


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
        """Resolve exchange ID from IBKR exchange code using factory pattern."""
        try:
            exchange_local_repo = self.factory.exchange_local_repo
            
            # Map IBKR exchange codes to standard names
            exchange_name_map = {
                'SMART': 'SMART',
                'NASDAQ': 'NASDAQ',
                'NYSE': 'NYSE',
                'TSE': 'TSE',
                'LSE': 'LSE',
            }
            
            exchange_name = exchange_name_map.get(ibkr_exchange, ibkr_exchange)
            exchange_object = exchange_local_repo.get_or_create(exchange_name)
            
            return exchange_object.id if exchange_object else 1
        except Exception as e:
            print(f"Error resolving exchange ID for {ibkr_exchange}: {e}")
            return 1

    def _resolve_company_id(self, symbol: str, contract_details: ContractDetails) -> int:
        """Resolve company ID from IBKR data using factory pattern."""
        try:
            company_local_repo = self.factory.company_local_repo
            
            # Extract company name from contract details
            company_name = getattr(contract_details, 'longName', f"{symbol} Company")
            
            # Create or get company
            company_object = company_local_repo.get_or_create(company_name)
            
            return company_object.id if company_object else 1
        except Exception as e:
            print(f"Error resolving company ID for {symbol}: {e}")
            return 1
    
