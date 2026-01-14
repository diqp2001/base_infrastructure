"""
IBKR Commodity Repository - Interactive Brokers implementation for Commodities.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.domain.ports.finance.financial_assets.commodity_port import CommodityPort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.domain.entities.finance.financial_assets.commodity import Commodity


class IBKRCommodityRepository(IBKRFinancialAssetRepository, CommodityPort):
    """
    IBKR implementation of CommodityPort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, local_repo: CommodityPort):
        """
        Initialize IBKR Commodity Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            local_repo: Local repository implementing CommodityPort for persistence
        """
        self.ibkr = ibkr_client
        self.local_repo = local_repo

    def get_or_create(self, symbol: str) -> Optional[Commodity]:
        """
        Get or create a commodity by symbol using IBKR API.
        
        Args:
            symbol: The commodity symbol (e.g., 'GC', 'CL', 'SI' for futures)
            
        Returns:
            Commodity entity or None if creation/retrieval failed
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
            print(f"Error in IBKR get_or_create for commodity symbol {symbol}: {e}")
            return None

    def get_by_symbol(self, symbol: str) -> Optional[Commodity]:
        """Get commodity by symbol (delegates to local repository)."""
        return self.local_repo.get_by_symbol(symbol)

    def get_by_id(self, entity_id: int) -> Optional[Commodity]:
        """Get commodity by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Commodity]:
        """Get all commodities (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Commodity) -> Optional[Commodity]:
        """Add commodity entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Commodity) -> Optional[Commodity]:
        """Update commodity entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete commodity entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def _fetch_contract(self, symbol: str) -> Optional[Contract]:
        """
        Fetch commodity contract from IBKR API.
        
        Args:
            symbol: Commodity symbol
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            
            # Determine if it's a futures contract or spot commodity
            if self._is_futures_symbol(symbol):
                contract.secType = "FUT"
                contract.symbol = self._extract_commodity_root(symbol)
                contract.exchange = self._get_commodity_exchange(symbol)
                contract.lastTradeDateOrContractMonth = self._extract_expiry_from_symbol(symbol)
            else:
                # Spot commodity or commodity index
                contract.secType = "CMDTY"  # or "IND" for indices
                contract.symbol = symbol
                contract.exchange = self._get_commodity_exchange(symbol)
            
            contract.currency = "USD"  # Most commodities priced in USD
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR commodity contract for {symbol}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[ContractDetails]:
        """
        Fetch commodity contract details from IBKR API.
        
        Args:
            contract: IBKR Contract object
            
        Returns:
            ContractDetails object or None if not found
        """
        try:
            # Mock implementation - in real code use self.ibkr.reqContractDetails()
            contract_details = ContractDetails()
            contract_details.contract = contract
            contract_details.marketName = "Commodity Market"
            
            commodity_info = self._get_commodity_info(contract.symbol)
            contract_details.longName = commodity_info['name']
            contract_details.minTick = commodity_info['min_tick']
            contract_details.priceMagnifier = commodity_info['multiplier']
            contract_details.orderTypes = "LMT,MKT,STP"
            
            return contract_details
        except Exception as e:
            print(f"Error fetching IBKR commodity contract details: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details: ContractDetails) -> Optional[Commodity]:
        """
        Convert IBKR contract and details directly to domain entity.
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object
            
        Returns:
            Commodity domain entity or None if conversion failed
        """
        try:
            commodity_info = self._get_commodity_info(contract.symbol)
            
            return Commodity(
                id=None,  # Let database generate
                symbol=contract.symbol,
                name=commodity_info['name'],
                commodity_type=commodity_info['type'],
                unit_of_measurement=commodity_info['unit'],
                exchange=contract.exchange,
                currency=contract.currency,
                contract_size=commodity_info['contract_size'],
                tick_size=Decimal(str(contract_details.minTick)),
                # IBKR-specific fields
                ibkr_contract_id=getattr(contract, 'conId', None),
                ibkr_local_symbol=getattr(contract, 'localSymbol', ''),
                ibkr_trading_class=getattr(contract, 'tradingClass', ''),
                ibkr_multiplier=contract_details.priceMagnifier,
                ibkr_expiry_date=getattr(contract, 'lastTradeDateOrContractMonth', None)
            )
        except Exception as e:
            print(f"Error converting IBKR commodity contract to domain entity: {e}")
            return None

    def _is_futures_symbol(self, symbol: str) -> bool:
        """Check if symbol represents a futures contract."""
        # Simple heuristic - futures typically have month/year codes
        return any(char.isdigit() for char in symbol) and len(symbol) > 2

    def _extract_commodity_root(self, symbol: str) -> str:
        """Extract commodity root symbol from futures symbol."""
        # Remove month/year codes
        return ''.join(c for c in symbol if c.isalpha())

    def _extract_expiry_from_symbol(self, symbol: str) -> str:
        """Extract expiry date from commodity futures symbol."""
        # Simplified extraction - real implementation would be more sophisticated
        digits = ''.join(c for c in symbol if c.isdigit())
        if len(digits) >= 2:
            # Assume year format YY
            year = "20" + digits[:2]
            month = digits[2:4] if len(digits) >= 4 else "12"
            return f"{year}{month.zfill(2)}"
        return "202412"  # Default

    def _get_commodity_exchange(self, symbol: str) -> str:
        """Get appropriate exchange for commodity symbol."""
        exchange_map = {
            'GC': 'COMEX',    # Gold
            'SI': 'COMEX',    # Silver
            'CL': 'NYMEX',    # Crude Oil
            'NG': 'NYMEX',    # Natural Gas
            'ZW': 'CBOT',     # Wheat
            'ZC': 'CBOT',     # Corn
            'ZS': 'CBOT',     # Soybeans
            'HG': 'COMEX',    # Copper
            'PA': 'NYMEX',    # Palladium
            'PL': 'NYMEX',    # Platinum
        }
        commodity_root = self._extract_commodity_root(symbol)
        return exchange_map.get(commodity_root, 'COMEX')

    def _get_commodity_info(self, symbol: str) -> dict:
        """Get commodity information for IBKR symbols."""
        commodity_data = {
            'GC': {
                'name': 'Gold Futures',
                'type': 'PRECIOUS_METAL',
                'unit': 'troy_ounces',
                'contract_size': 100,
                'min_tick': 0.10,
                'multiplier': 100
            },
            'SI': {
                'name': 'Silver Futures',
                'type': 'PRECIOUS_METAL',
                'unit': 'troy_ounces',
                'contract_size': 5000,
                'min_tick': 0.005,
                'multiplier': 5000
            },
            'CL': {
                'name': 'Crude Oil Futures',
                'type': 'ENERGY',
                'unit': 'barrels',
                'contract_size': 1000,
                'min_tick': 0.01,
                'multiplier': 1000
            },
            'NG': {
                'name': 'Natural Gas Futures',
                'type': 'ENERGY',
                'unit': 'mmbtu',
                'contract_size': 10000,
                'min_tick': 0.001,
                'multiplier': 10000
            },
            'ZW': {
                'name': 'Wheat Futures',
                'type': 'AGRICULTURAL',
                'unit': 'bushels',
                'contract_size': 5000,
                'min_tick': 0.25,
                'multiplier': 50
            },
            'ZC': {
                'name': 'Corn Futures',
                'type': 'AGRICULTURAL',
                'unit': 'bushels',
                'contract_size': 5000,
                'min_tick': 0.25,
                'multiplier': 50
            },
            'ZS': {
                'name': 'Soybean Futures',
                'type': 'AGRICULTURAL',
                'unit': 'bushels',
                'contract_size': 5000,
                'min_tick': 0.25,
                'multiplier': 50
            },
            'HG': {
                'name': 'Copper Futures',
                'type': 'INDUSTRIAL_METAL',
                'unit': 'pounds',
                'contract_size': 25000,
                'min_tick': 0.0005,
                'multiplier': 25000
            }
        }
        
        return commodity_data.get(symbol, {
            'name': f'{symbol} Commodity',
            'type': 'OTHER',
            'unit': 'units',
            'contract_size': 1,
            'min_tick': 0.01,
            'multiplier': 1
        })

    def get_precious_metals(self) -> List[Commodity]:
        """Get precious metal commodities."""
        metals = ['GC', 'SI', 'PA', 'PL']
        commodities = []
        
        for symbol in metals:
            commodity = self.get_or_create(symbol)
            if commodity:
                commodities.append(commodity)
        
        return commodities

    def get_energy_commodities(self) -> List[Commodity]:
        """Get energy commodities."""
        energy = ['CL', 'NG', 'HO', 'RB']
        commodities = []
        
        for symbol in energy:
            commodity = self.get_or_create(symbol)
            if commodity:
                commodities.append(commodity)
        
        return commodities

    def get_agricultural_commodities(self) -> List[Commodity]:
        """Get agricultural commodities."""
        agriculture = ['ZW', 'ZC', 'ZS', 'CT', 'CC', 'KC']
        commodities = []
        
        for symbol in agriculture:
            commodity = self.get_or_create(symbol)
            if commodity:
                commodities.append(commodity)
        
        return commodities