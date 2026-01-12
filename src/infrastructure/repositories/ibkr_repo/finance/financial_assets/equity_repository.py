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
from src.infrastructure.repositories.ibkr_repo.base_ibkr_repository import BaseIBKRRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_base_repository import FinancialAssetBaseRepository
from src.domain.entities.finance.financial_assets.equity import Equity


class IBKREquityRepository(FinancialAssetBaseRepository, EquityPort):
    """
    IBKR implementation of EquityPort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, local_repo: EquityPort):
        """
        Initialize IBKR Equity Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            local_repo: Local repository implementing EquityPort for persistence
        """
        self.ibkr = ibkr_client
        self.local_repo = local_repo

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

    def _fetch_contract_details(self, contract: Contract) -> Optional[ContractDetails]:
        """
        Fetch equity contract details from IBKR API.
        
        Args:
            contract: IBKR Contract object
            
        Returns:
            ContractDetails object or None if not found
        """
        try:
            # Mock implementation - in real code use self.ibkr.reqContractDetails()
            contract_details = ContractDetails()
            contract_details.contract = contract
            contract_details.marketName = "Stock Market"
            contract_details.minTick = 0.01
            contract_details.priceMagnifier = 1
            contract_details.orderTypes = "LMT,MKT,STP,TRAIL"
            
            # Get equity-specific info
            equity_info = self._get_equity_info(contract.symbol)
            contract_details.longName = equity_info['company_name']
            contract_details.industry = equity_info['industry']
            contract_details.category = equity_info['category']
            
            # Equity-specific details
            contract_details.underlyingConId = None
            contract_details.multiplier = "1"
            contract_details.callable = False
            
            return contract_details
        except Exception as e:
            print(f"Error fetching IBKR equity contract details: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details: ContractDetails) -> Optional[Equity]:
        """
        Convert IBKR contract and details directly to domain entity.
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object
            
        Returns:
            Equity domain entity or None if conversion failed
        """
        try:
            equity_info = self._get_equity_info(contract.symbol)
            
            return Equity(
                id=None,  # Let database generate
                symbol=contract.symbol,
                name=equity_info['company_name'],
                company_id=self._resolve_company_id(contract.symbol, contract_details),
                exchange_id=self._resolve_exchange_id(contract.exchange),
                share_class=equity_info.get('share_class', 'Common'),
                shares_outstanding=equity_info.get('shares_outstanding'),
                market_cap=equity_info.get('market_cap'),
                sector=equity_info.get('sector'),
                industry=equity_info.get('industry'),
                dividend_yield=equity_info.get('dividend_yield'),
                pe_ratio=equity_info.get('pe_ratio'),
                # IBKR-specific fields
                ibkr_contract_id=getattr(contract, 'conId', None),
                ibkr_local_symbol=getattr(contract, 'localSymbol', ''),
                ibkr_trading_class=getattr(contract, 'tradingClass', ''),
                ibkr_primary_exchange=getattr(contract, 'primaryExchange', ''),
                ibkr_industry=getattr(contract_details, 'industry', ''),
                ibkr_category=getattr(contract_details, 'category', ''),
                ibkr_callable=getattr(contract_details, 'callable', False)
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

    def _resolve_company_id(self, symbol: str, contract_details: ContractDetails) -> int:
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