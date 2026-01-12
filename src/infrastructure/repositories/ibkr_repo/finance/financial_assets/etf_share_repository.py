"""
IBKR ETF Share Repository - Interactive Brokers implementation for ETF Shares.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.domain.ports.finance.financial_assets.share.etf_share_port import EtfSharePort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_repository import BaseIBKRRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.share_repository import ShareRepository
from src.domain.entities.finance.financial_assets.share.etf_share import EtfShare


class IBKREtfShareRepository(ShareRepository, EtfSharePort):
    """
    IBKR implementation of EtfSharePort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, local_repo: EtfSharePort):
        """
        Initialize IBKR ETF Share Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            local_repo: Local repository implementing EtfSharePort for persistence
        """
        self.ibkr = ibkr_client
        self.local_repo = local_repo

    def get_or_create(self, symbol: str) -> Optional[EtfShare]:
        """
        Get or create an ETF share by symbol using IBKR API.
        
        Args:
            symbol: The ETF ticker symbol (e.g., 'SPY', 'QQQ', 'VTI')
            
        Returns:
            EtfShare entity or None if creation/retrieval failed
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
            print(f"Error in IBKR get_or_create for ETF symbol {symbol}: {e}")
            return None

    def get_by_ticker(self, ticker: str) -> List[EtfShare]:
        """Get ETF share by ticker (delegates to local repository)."""
        return self.local_repo.get_by_ticker(ticker)

    def get_by_id(self, entity_id: int) -> Optional[EtfShare]:
        """Get ETF share by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[EtfShare]:
        """Get all ETF shares (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: EtfShare) -> Optional[EtfShare]:
        """Add ETF share entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity_id: int, **kwargs) -> Optional[EtfShare]:
        """Update ETF share entity (delegates to local repository)."""
        return self.local_repo.update(entity_id, **kwargs)

    def delete(self, entity_id: int) -> bool:
        """Delete ETF share entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def exists_by_ticker(self, ticker: str) -> bool:
        """Check if ETF share exists by ticker (delegates to local repository)."""
        return self.local_repo.exists_by_ticker(ticker)

    def _fetch_contract(self, symbol: str) -> Optional[Contract]:
        """
        Fetch ETF contract from IBKR API.
        
        Args:
            symbol: ETF ticker symbol
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            contract.symbol = symbol.upper()
            contract.secType = "STK"  # ETFs are treated as stocks in IBKR
            contract.exchange = "SMART"  # IBKR smart routing
            contract.currency = "USD"
            
            # Apply IBKR-specific ETF rules
            contract = self._apply_ibkr_etf_rules(contract, symbol)
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR ETF contract for {symbol}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[ContractDetails]:
        """
        Fetch ETF contract details from IBKR API.
        
        Args:
            contract: IBKR Contract object
            
        Returns:
            ContractDetails object or None if not found
        """
        try:
            # Mock implementation - in real code use self.ibkr.reqContractDetails()
            contract_details = ContractDetails()
            contract_details.contract = contract
            contract_details.marketName = "ETF Market"
            contract_details.minTick = 0.01
            contract_details.priceMagnifier = 1
            contract_details.orderTypes = "LMT,MKT,STP,TRAIL"
            contract_details.longName = f"{contract.symbol} ETF"
            contract_details.industry = "Exchange Traded Funds"
            contract_details.category = "ETF"
            
            # ETF-specific details
            contract_details.underlyingConId = None  # Would contain underlying index contract ID
            contract_details.multiplier = "1"
            
            return contract_details
        except Exception as e:
            print(f"Error fetching IBKR ETF contract details: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details: ContractDetails) -> Optional[EtfShare]:
        """
        Convert IBKR contract and details directly to domain entity.
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object
            
        Returns:
            EtfShare domain entity or None if conversion failed
        """
        try:
            return EtfShare(
                id=None,  # Let database generate
                ticker=contract.symbol,
                exchange_id=self._resolve_exchange_id(contract.exchange),
                company_id=self._resolve_fund_company_id(contract.symbol, contract_details),
                start_date=None,
                end_date=None,
                # ETF-specific fields
                fund_name=getattr(contract_details, 'longName', f"{contract.symbol} ETF"),
                expense_ratio=self._estimate_expense_ratio(contract.symbol),
                aum=None,  # Assets Under Management - would need separate data source
                inception_date=None,  # Would need separate data source
                underlying_index=self._resolve_underlying_index(contract.symbol),
                # IBKR-specific fields
                ibkr_contract_id=getattr(contract, 'conId', None),
                ibkr_local_symbol=getattr(contract, 'localSymbol', ''),
                ibkr_trading_class=getattr(contract, 'tradingClass', ''),
                ibkr_underlying_con_id=getattr(contract_details, 'underlyingConId', None)
            )
        except Exception as e:
            print(f"Error converting IBKR ETF contract to domain entity: {e}")
            return None

    def _apply_ibkr_etf_rules(self, contract: Contract, original_symbol: str) -> Contract:
        """Apply IBKR-specific ETF symbol resolution and exchange rules."""
        symbol = original_symbol.upper()
        
        # Handle special ETF cases
        if symbol in ['SPY', 'IVV', 'VOO']:  # S&P 500 ETFs
            contract.primaryExchange = "ARCA"
        elif symbol in ['QQQ', 'QQQM']:  # NASDAQ 100 ETFs
            contract.primaryExchange = "NASDAQ"
        elif symbol.startswith('VT'):  # Vanguard ETFs
            contract.primaryExchange = "ARCA"
        elif symbol.startswith('IWM'):  # Russell ETFs
            contract.primaryExchange = "ARCA"
            
        return contract

    def _resolve_exchange_id(self, ibkr_exchange: str) -> int:
        """Resolve exchange ID from IBKR exchange code."""
        exchange_map = {
            'SMART': 1,
            'ARCA': 2,
            'NASDAQ': 3,
            'NYSE': 4,
        }
        return exchange_map.get(ibkr_exchange, 1)

    def _resolve_fund_company_id(self, symbol: str, contract_details: ContractDetails) -> int:
        """Resolve fund management company ID."""
        # Map common ETF symbols to fund companies
        fund_company_map = {
            'SPY': 1,    # State Street
            'VOO': 2,    # Vanguard
            'IVV': 3,    # BlackRock/iShares
            'QQQ': 4,    # Invesco
            'VTI': 2,    # Vanguard
            'IWM': 3,    # BlackRock/iShares
        }
        
        # Check for common prefixes
        if symbol.startswith('V'):  # Vanguard
            return 2
        elif symbol.startswith('I'):  # iShares/BlackRock
            return 3
        elif symbol.startswith('SPY'):  # State Street
            return 1
        
        return fund_company_map.get(symbol, 1)  # Default

    def _resolve_underlying_index(self, symbol: str) -> Optional[str]:
        """Resolve the underlying index for common ETFs."""
        index_map = {
            'SPY': 'SPX',     # S&P 500
            'VOO': 'SPX',     # S&P 500
            'IVV': 'SPX',     # S&P 500
            'QQQ': 'NDX',     # NASDAQ 100
            'VTI': 'VTI',     # Total Stock Market
            'IWM': 'RUT',     # Russell 2000
            'EFA': 'EAFE',    # MSCI EAFE
            'EEM': 'EM',      # MSCI Emerging Markets
        }
        return index_map.get(symbol)

    def _estimate_expense_ratio(self, symbol: str) -> Optional[Decimal]:
        """Estimate expense ratio for common ETFs."""
        # Common expense ratios (would be better to fetch from real data source)
        expense_ratios = {
            'SPY': Decimal('0.0945'),   # 0.0945%
            'VOO': Decimal('0.03'),     # 0.03%
            'IVV': Decimal('0.03'),     # 0.03%
            'QQQ': Decimal('0.20'),     # 0.20%
            'VTI': Decimal('0.03'),     # 0.03%
            'IWM': Decimal('0.19'),     # 0.19%
        }
        return expense_ratios.get(symbol)

    def get_popular_etfs(self) -> List[EtfShare]:
        """Get popular ETFs from IBKR."""
        popular_symbols = [
            'SPY', 'VOO', 'IVV',  # S&P 500
            'QQQ', 'VTI',         # NASDAQ/Total Market
            'IWM',                # Small Cap
            'EFA', 'EEM'          # International
        ]
        
        etfs = []
        for symbol in popular_symbols:
            etf = self.get_or_create(symbol)
            if etf:
                etfs.append(etf)
        
        return etfs