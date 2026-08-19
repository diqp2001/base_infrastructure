from datetime import datetime
import os
from typing import Any, Optional, List

from ibapi.contract import Contract

from src.domain.entities.finance.financial_assets.derivatives.future.bond_future import BondFuture
from src.domain.ports.finance.financial_assets.derivatives.future.bond_future_port import BondFuturePort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.infrastructure.repositories.mappers.finance.financial_assets.derivatives.future.bond_future_mapper import BondFutureMapper


class IBKRBondFutureRepository(IBKRFinancialAssetRepository, BondFuturePort):
    """IBKR implementation for BondFuture — fetches contract from IBKR and delegates persistence to local repo."""

    def __init__(self, ibkr_client, factory=None):
        self.ib_broker = ibkr_client
        self.factory = factory
        self.mapper = BondFutureMapper()
        self.local_repo = self.factory._local_repositories.get('BondFuture') if factory else None

    @property
    def entity_class(self):
        return self.mapper.entity_class

    @property
    def model_class(self):
        return self.mapper.model_class

    def _create_or_get(self, symbol: str, **kwargs) -> Optional[BondFuture]:
        try:
            if self.local_repo:
                existing = self.local_repo.get_by_symbol(symbol)
                if existing:
                    return existing

            contract = self._fetch_contract(symbol)
            if not contract:
                return None

            contract_details_list = self._fetch_contract_details(contract)
            if not contract_details_list:
                return None

            contract_detail = next(
                (c for c in contract_details_list if c.get('local_symbol') == symbol),
                contract_details_list[0]
            )

            entity = self._contract_to_domain(contract, contract_detail)
            if not entity:
                return None

            if self.local_repo:
                return self.local_repo.add(entity)
            return entity

        except Exception as e:
            print(f"Error in IBKRBondFutureRepository._create_or_get for {symbol}: {e}_{os.path.abspath(__file__)}")
            return None

    def get_by_symbol(self, symbol: str) -> Optional[BondFuture]:
        return self.local_repo.get_by_symbol(symbol) if self.local_repo else None

    def get_by_id(self, entity_id: int) -> Optional[BondFuture]:
        return self.local_repo.get_by_id(entity_id) if self.local_repo else None

    def get_all(self) -> List[BondFuture]:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: BondFuture) -> Optional[BondFuture]:
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: BondFuture) -> Optional[BondFuture]:
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, entity_id: int) -> bool:
        return self.local_repo.delete(entity_id) if self.local_repo else False
    def build_future_contract_from_local_symbol(self,local_symbol: str) -> Contract:
            """
            Converts IBKR local_symbol like 'ESZ6'
            into a properly formatted IBKR FUT Contract.
            """
            MONTH_CODES = {
            "F": "01",  # January
            "G": "02",  # February
            "H": "03",  # March
            "J": "04",  # April
            "K": "05",  # May
            "M": "06",  # June
            "N": "07",  # July
            "Q": "08",  # August
            "U": "09",  # September
            "V": "10",  # October
            "X": "11",  # November
            "Z": "12",  # December
        }
            # Extract parts
            root_symbol = local_symbol[:-2]
            month_code = local_symbol[-2]
            year_digit = local_symbol[-1]
    
            if month_code not in MONTH_CODES:
                raise ValueError(f"Invalid month code: {month_code}")
    
            # Robust year handling (works across decades)
            current_year = datetime.utcnow().year
            current_decade = (current_year // 10) * 10
            year = current_decade + int(year_digit)
    
            # If decoded year is in the past, assume next decade
            if year < current_year - 1:
                year += 10
    
            expiry = f"{year}{MONTH_CODES[month_code]}"
    
            
    
            return expiry
    def _fetch_contract(self, symbol: str) -> Optional[Contract]:
        try:
            root = self._extract_root_symbol(symbol)
            contract = Contract()
            contract.symbol = symbol
            contract.tradingClass = root
            contract.secType = "FUT"
            contract.exchange = "CME"
            contract.includeExpired = True
            return contract
        except Exception as e:
            print(f"Error building IBKR contract for bond future {symbol}: {e}_{os.path.abspath(__file__)}")
            return None

    def _fetch_historical_contract(self, symbol: str) -> Optional[Contract]:
        """Contract for reqHistoricalData: resolved via conId to avoid IBKR ambiguity."""
        try:
            details_contract = self._fetch_contract(symbol)
            contract_details_list = self._fetch_contract_details(details_contract)
            if not contract_details_list:
                return None
            detail = next(
                (c for c in contract_details_list if c.get('local_symbol') == symbol),
                None,
            )
            if not detail:
                return None
            con_id = detail.get('contract_id')
            if not con_id:
                return None
            contract = Contract()
            contract.conId = con_id
            contract.exchange = detail.get('exchange', 'CME')
            return contract
        except Exception as e:
            print(f"Error building historical IBKR contract for bond future {symbol}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[List[dict]]:
        try:
            details = self.ib_broker.get_contract_details(contract, timeout=15)
            return details if details else None
        except Exception as e:
            print(f"Error fetching IBKR contract details: {e}")
            return None

    # Root symbol → IBKR underlying index symbol
    _UNDERLYING_MAP = {
        'SR3': 'SOFR3', 'SR1': 'SOFR1',
        'ZB': 'USB', 'ZN': 'TNX', 'ZT': 'IRX', 'ZF': 'FVX',
    }

    def _contract_to_domain(self, contract: Contract, contract_detail: Any) -> Optional[BondFuture]:
        try:
            if not contract_detail:
                return None
            currency = self._get_or_create_currency(
                contract_detail.get('currency', 'USD'),
                f"{contract_detail.get('currency', 'USD')} Currency",
            )
            exchange = self._get_or_create_exchange(contract_detail.get('exchange', 'CME'))
            root = self._extract_root_symbol(contract.symbol)
            underlying = self._get_or_create_underlying(self._UNDERLYING_MAP.get(root, root))
            start_date = (
                contract_detail.get('real_expiration_date')
                or contract_detail.get('last_trade_date')
                or datetime.now().date()
            )
            return BondFuture(
                id=None,
                name=f"{contract_detail.get('local_symbol', contract.symbol)} Bond Future",
                symbol=contract_detail.get('local_symbol', contract.symbol),
                exchange_id=exchange.id if exchange else None,
                currency_id=currency.id if currency else None,
                underlying_asset_id=underlying.id if underlying else None,
                contract_size=contract_detail.get('contract_size'),
                start_date=start_date,
            )
        except Exception as e:
            print(f"Error converting IBKR contract to BondFuture: {e}_{os.path.abspath(__file__)}")
            return None

    def _get_or_create_currency(self, iso_code: str, name: str):
        try:
            if self.factory and hasattr(self.factory, 'currency_ibkr_repo'):
                repo = self.factory.currency_ibkr_repo
                if repo:
                    return repo._create_or_get(iso_code)
        except Exception as e:
            print(f"Error getting/creating currency {iso_code}: {e}")
        return None

    def _get_or_create_exchange(self, exchange_code: str):
        try:
            if self.factory and hasattr(self.factory, 'exchange_ibkr_repo'):
                repo = self.factory.exchange_ibkr_repo
                if repo:
                    return repo._create_or_get(exchange_code)
        except Exception as e:
            print(f"Error getting/creating exchange {exchange_code}: {e}")
        return None

    def _get_or_create_underlying(self, index_symbol: str):
        try:
            if self.factory and hasattr(self.factory, 'index_bond_ibkr_repo'):
                repo = self.factory.index_bond_ibkr_repo
                if repo:
                    return repo._create_or_get(index_symbol)
        except Exception as e:
            print(f"Error getting/creating underlying index {index_symbol}: {e}")
        return None

    def _extract_root_symbol(self, local_symbol: str) -> str:
        """Strip last 2 chars (month code + year digit) to get root (e.g. 'ZBZ6' → 'ZB')."""
        return local_symbol[:-2]

    def _build_expiry_from_local_symbol(self, local_symbol: str) -> str:
        MONTH_CODES = {
            "F": "01", "G": "02", "H": "03", "J": "04", "K": "05", "M": "06",
            "N": "07", "Q": "08", "U": "09", "V": "10", "X": "11", "Z": "12",
        }
        from datetime import datetime
        if len(local_symbol) < 2:
            return ""
        month_code = local_symbol[-2]
        year_digit = local_symbol[-1]
        if month_code not in MONTH_CODES:
            return ""
        month = MONTH_CODES[month_code]
        current_year = datetime.utcnow().year
        decade = (current_year // 10) * 10
        year = decade + int(year_digit)
        if year < current_year - 1:
            year += 10
        return f"{year}{month}"
