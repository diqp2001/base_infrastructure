"""
IBKR Equity Repository - Interactive Brokers implementation for Equities.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.domain.ports.finance.financial_assets.equity_port import EquityPort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.domain.entities.finance.financial_assets.equity import Equity


class IBKREquityRepository(IBKRFinancialAssetRepository, EquityPort):
    """
    IBKR implementation of EquityPort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, local_repo: EquityPort):
        """
        Initialize IBKR Equity Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client (InteractiveBrokersBroker instance)
            local_repo: Local repository implementing EquityPort for persistence
        """
        self.ib_broker = ibkr_client  # Use ib_broker for consistency with reference implementation
        self.local_repo = local_repo
    @property
    def entity_class(self):
        """Return the domain entity class for Equity."""
        return Equity
    def get_or_create(self, symbol: str) -> Optional[Equity]:
        """
        Get or create an equity by symbol using IBKR API.
        
        Args:
            symbol: The equity symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')
            
        Returns:
            Equity entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            existing = self.local_repo.get_by_symbol(symbol)
            if existing:
                return existing
            
            # 2. Fetch from IBKR API
            contract = self._fetch_contract(symbol)
            if not contract:
                return None
                
            # 3. Get contract details from IBKR
            contract_details_list = self._fetch_contract_details(contract)
            if not contract_details_list:
                return None
                
            # 4. Apply IBKR-specific rules and convert to domain entity
            entity = self._contract_to_domain(contract, contract_details_list)
            if not entity:
                return None
                
            # 5. Delegate persistence to local repository
            return self.local_repo.add(entity)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for equity symbol {symbol}: {e}")
            return None

    def get_by_symbol(self, symbol: str) -> Optional[Equity]:
        """Get equity by symbol (delegates to local repository)."""
        return self.local_repo.get_by_symbol(symbol)

    def get_by_id(self, entity_id: int) -> Optional[Equity]:
        """Get equity by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Equity]:
        """Get all equities (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Equity) -> Optional[Equity]:
        """Add equity entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Equity) -> Optional[Equity]:
        """Update equity entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete equity entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def _fetch_contract(self, symbol: str) -> Optional[Contract]:
        """
        Fetch equity contract from IBKR API.
        
        Args:
            symbol: Equity ticker symbol
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            contract.symbol = symbol.upper()
            contract.secType = "STK"
            contract.exchange = "SMART"  # IBKR smart routing
            contract.currency = "USD"
            
            # Apply IBKR-specific equity rules
            contract = self._apply_ibkr_equity_rules(contract, symbol)
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR equity contract for {symbol}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[List[dict]]:
        """
        Fetch equity contract details from IBKR API using broker method.
        
        Args:
            contract: IBKR Contract object
            
        Returns:
            List of contract details dictionaries or None if not found
        """
        try:
            # Use the broker's get_contract_details method (like in reference implementation)
            contract_details = self.ib_broker.get_contract_details(contract, timeout=15)
            
            if contract_details and len(contract_details) > 0:
                return contract_details
            else:
                print(f"No contract details received for {contract.symbol}")
                return None
                
        except Exception as e:
            print(f"Error fetching IBKR equity contract details: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details_list: List[dict]) -> Optional[Equity]:
        """
        Convert IBKR contract and details to domain entity using real API data.
        
        Args:
            contract: IBKR Contract object
            contract_details_list: List of contract details dictionaries from IBKR API
            
        Returns:
            Equity domain entity or None if conversion failed
        """
        try:
            # Use the first contract details result
            contract_details = contract_details_list[0] if contract_details_list else {}
            
            # Extract data from IBKR API response
            symbol = contract.symbol
            company_name = contract_details.get('long_name', f"{symbol} Inc.")
            
            # Get additional equity info
            equity_info = self._get_equity_info(symbol)
            
            return Equity(
                id=None,  # Let database generate
                symbol=symbol,
                name=company_name,
                company_id=self._resolve_company_id(symbol, contract_details),
                exchange_id=self._resolve_exchange_id(contract.exchange),
                share_class=equity_info.get('share_class', 'Common'),
                shares_outstanding=equity_info.get('shares_outstanding'),
                market_cap=equity_info.get('market_cap'),
                sector=equity_info.get('sector'),
                industry=equity_info.get('industry'),
                dividend_yield=equity_info.get('dividend_yield'),
                pe_ratio=equity_info.get('pe_ratio'),
                # IBKR-specific fields
                ibkr_contract_id=contract_details.get('contract_id'),
                ibkr_local_symbol=contract_details.get('local_symbol', ''),
                ibkr_trading_class=contract_details.get('trading_class', ''),
                ibkr_primary_exchange=contract_details.get('primary_exchange', ''),
                ibkr_industry=contract_details.get('industry', ''),
                ibkr_category=contract_details.get('category', ''),
                ibkr_callable=contract_details.get('callable', False)
            )
        except Exception as e:
            print(f"Error converting IBKR equity contract to domain entity: {e}")
            return None

    def _apply_ibkr_equity_rules(self, contract: Contract, original_symbol: str) -> Contract:
        """Apply IBKR-specific equity symbol resolution and exchange rules."""
        symbol = original_symbol.upper()
        
        # Handle special equity cases
        if '.' in symbol:
            # Handle different share classes
            base_symbol, class_suffix = symbol.split('.', 1)
            contract.symbol = base_symbol
            if class_suffix in ['A', 'B', 'C']:
                contract.symbol = f"{base_symbol} {class_suffix}"
        
        # Set primary exchange for better execution
        primary_exchanges = {
            'AAPL': 'NASDAQ',
            'MSFT': 'NASDAQ',
            'GOOGL': 'NASDAQ',
            'AMZN': 'NASDAQ',
            'TSLA': 'NASDAQ',
            'META': 'NASDAQ',
            'NVDA': 'NASDAQ',
            'JPM': 'NYSE',
            'JNJ': 'NYSE',
            'V': 'NYSE',
            'PG': 'NYSE',
            'UNH': 'NYSE',
            'HD': 'NYSE',
            'DIS': 'NYSE',
            'BAC': 'NYSE'
        }
        
        if symbol in primary_exchanges:
            contract.primaryExchange = primary_exchanges[symbol]
            
        return contract

    def _resolve_exchange_id(self, ibkr_exchange: str) -> int:
        """Resolve exchange ID from IBKR exchange code."""
        exchange_map = {
            'SMART': 1,
            'NASDAQ': 2,
            'NYSE': 3,
            'ARCA': 4,
            'BATS': 5,
        }
        return exchange_map.get(ibkr_exchange, 1)

    def _resolve_company_id(self, symbol: str, contract_details: dict) -> int:
        """Resolve company ID from equity data."""
        # This would typically involve looking up or creating company entities
        # For now, return a default mapping
        company_map = {
            'AAPL': 1,   # Apple Inc.
            'MSFT': 2,   # Microsoft Corporation
            'GOOGL': 3,  # Alphabet Inc.
            'AMZN': 4,   # Amazon.com Inc.
            'TSLA': 5,   # Tesla Inc.
            'META': 6,   # Meta Platforms Inc.
            'NVDA': 7,   # NVIDIA Corporation
            'JPM': 8,    # JPMorgan Chase & Co.
            'JNJ': 9,    # Johnson & Johnson
            'V': 10,     # Visa Inc.
        }
        return company_map.get(symbol, 1)  # Default

    def _get_equity_info(self, symbol: str) -> dict:
        """Get equity information for common stocks."""
        equity_data = {
            'AAPL': {
                'company_name': 'Apple Inc.',
                'industry': 'Technology Hardware & Equipment',
                'category': 'Common Stock',
                'sector': 'Technology',
                'share_class': 'Common',
                'shares_outstanding': 15500000000,
                'market_cap': 3000000000000,
                'dividend_yield': Decimal('0.44'),
                'pe_ratio': Decimal('29.5')
            },
            'MSFT': {
                'company_name': 'Microsoft Corporation',
                'industry': 'Software',
                'category': 'Common Stock',
                'sector': 'Technology',
                'share_class': 'Common',
                'shares_outstanding': 7400000000,
                'market_cap': 2800000000000,
                'dividend_yield': Decimal('0.68'),
                'pe_ratio': Decimal('34.2')
            },
            'GOOGL': {
                'company_name': 'Alphabet Inc.',
                'industry': 'Interactive Media & Services',
                'category': 'Common Stock',
                'sector': 'Technology',
                'share_class': 'Class A',
                'shares_outstanding': 12800000000,
                'market_cap': 2000000000000,
                'dividend_yield': None,
                'pe_ratio': Decimal('25.1')
            },
            'AMZN': {
                'company_name': 'Amazon.com Inc.',
                'industry': 'Internet & Direct Marketing Retail',
                'category': 'Common Stock',
                'sector': 'Consumer Discretionary',
                'share_class': 'Common',
                'shares_outstanding': 10400000000,
                'market_cap': 1700000000000,
                'dividend_yield': None,
                'pe_ratio': Decimal('52.8')
            },
            'TSLA': {
                'company_name': 'Tesla Inc.',
                'industry': 'Automobiles',
                'category': 'Common Stock',
                'sector': 'Consumer Discretionary',
                'share_class': 'Common',
                'shares_outstanding': 3100000000,
                'market_cap': 800000000000,
                'dividend_yield': None,
                'pe_ratio': Decimal('65.4')
            }
        }
        
        return equity_data.get(symbol, {
            'company_name': f'{symbol} Inc.',
            'industry': 'Unknown',
            'category': 'Common Stock',
            'sector': 'Unknown',
            'share_class': 'Common',
            'shares_outstanding': None,
            'market_cap': None,
            'dividend_yield': None,
            'pe_ratio': None
        })

    def get_sp500_equities(self) -> List[Equity]:
        """Get S&P 500 equities."""
        sp500_symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 
            'JPM', 'JNJ', 'V', 'PG', 'UNH', 'HD', 'DIS', 'BAC'
        ]
        
        equities = []
        for symbol in sp500_symbols:
            equity = self.get_or_create(symbol)
            if equity:
                equities.append(equity)
        
        return equities

    def get_tech_equities(self) -> List[Equity]:
        """Get technology sector equities."""
        tech_symbols = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'META', 'ORCL', 'CRM', 'ADBE']
        
        equities = []
        for symbol in tech_symbols:
            equity = self.get_or_create(symbol)
            if equity:
                equities.append(equity)
        
        return equities

    def get_financial_equities(self) -> List[Equity]:
        """Get financial sector equities."""
        financial_symbols = ['JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'AXP']
        
        equities = []
        for symbol in financial_symbols:
            equity = self.get_or_create(symbol)
            if equity:
                equities.append(equity)
        
        return equities