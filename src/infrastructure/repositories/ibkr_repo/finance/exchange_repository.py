"""
IBKR Exchange Repository - Interactive Brokers implementation for Exchanges.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List
from datetime import time

from ibapi.contract import Contract, ContractDetails

from src.domain.ports.finance.exchange_port import ExchangePort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_repository import BaseIBKRRepository
from src.domain.entities.finance.exchange import Exchange


class IBKRExchangeRepository(BaseIBKRRepository, ExchangePort):
    """
    IBKR implementation of ExchangePort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, local_repo: ExchangePort):
        """
        Initialize IBKR Exchange Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            local_repo: Local repository implementing ExchangePort for persistence
        """
        self.ibkr = ibkr_client
        self.local_repo = local_repo

    def get_or_create(self, exchange_code: str) -> Optional[Exchange]:
        """
        Get or create an exchange by code using IBKR API.
        
        Args:
            exchange_code: The exchange code (e.g., 'NYSE', 'NASDAQ', 'SMART')
            
        Returns:
            Exchange entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            existing = self.local_repo.get_by_code(exchange_code)
            if existing:
                return existing
            
            # 2. Create exchange entity with IBKR-specific data
            entity = self._create_exchange_entity(exchange_code)
            if not entity:
                return None
                
            # 3. Delegate persistence to local repository
            return self.local_repo.add(entity)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for exchange {exchange_code}: {e}")
            return None

    def get_by_code(self, exchange_code: str) -> Optional[Exchange]:
        """Get exchange by code (delegates to local repository)."""
        return self.local_repo.get_by_code(exchange_code)

    def get_by_id(self, entity_id: int) -> Optional[Exchange]:
        """Get exchange by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Exchange]:
        """Get all exchanges (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Exchange) -> Optional[Exchange]:
        """Add exchange entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Exchange) -> Optional[Exchange]:
        """Update exchange entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete exchange entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def _create_exchange_entity(self, exchange_code: str) -> Optional[Exchange]:
        """
        Create an exchange entity with IBKR-specific properties.
        
        Args:
            exchange_code: Exchange code from IBKR
            
        Returns:
            Exchange domain entity or None if creation failed
        """
        try:
            exchange_info = self._get_ibkr_exchange_info(exchange_code)
            if not exchange_info:
                return None
            
            return Exchange(
                id=None,  # Let database generate
                name=exchange_info['name'],
                code=exchange_code.upper(),
                country_id=exchange_info['country_id'],
                timezone=exchange_info['timezone'],
                currency=exchange_info['currency'],
                market_open_time=exchange_info['market_open'],
                market_close_time=exchange_info['market_close'],
                # IBKR-specific fields
                ibkr_exchange_code=exchange_code.upper(),
                ibkr_routing_type=exchange_info.get('routing_type', 'DIRECT'),
                ibkr_smart_routing=exchange_info.get('smart_routing', False),
                ibkr_supported_order_types=exchange_info.get('order_types', [])
            )
        except Exception as e:
            print(f"Error creating exchange entity for {exchange_code}: {e}")
            return None

    def _get_ibkr_exchange_info(self, exchange_code: str) -> Optional[dict]:
        """
        Get exchange information specific to IBKR.
        
        Args:
            exchange_code: IBKR exchange code
            
        Returns:
            Dictionary with exchange information
        """
        # IBKR exchange mapping
        ibkr_exchanges = {
            'NYSE': {
                'name': 'New York Stock Exchange',
                'country_id': 1,  # USA
                'timezone': 'America/New_York',
                'currency': 'USD',
                'market_open': time(9, 30),
                'market_close': time(16, 0),
                'routing_type': 'DIRECT',
                'smart_routing': True,
                'order_types': ['LMT', 'MKT', 'STP', 'TRAIL']
            },
            'NASDAQ': {
                'name': 'NASDAQ Stock Market',
                'country_id': 1,  # USA
                'timezone': 'America/New_York',
                'currency': 'USD',
                'market_open': time(9, 30),
                'market_close': time(16, 0),
                'routing_type': 'DIRECT',
                'smart_routing': True,
                'order_types': ['LMT', 'MKT', 'STP', 'TRAIL']
            },
            'SMART': {
                'name': 'IBKR Smart Routing',
                'country_id': 1,  # USA (primary)
                'timezone': 'America/New_York',
                'currency': 'USD',
                'market_open': time(9, 30),
                'market_close': time(16, 0),
                'routing_type': 'SMART',
                'smart_routing': True,
                'order_types': ['LMT', 'MKT', 'STP', 'TRAIL', 'REL', 'MIDPRICE']
            },
            'ARCA': {
                'name': 'NYSE Arca',
                'country_id': 1,  # USA
                'timezone': 'America/New_York',
                'currency': 'USD',
                'market_open': time(9, 30),
                'market_close': time(16, 0),
                'routing_type': 'DIRECT',
                'smart_routing': False,
                'order_types': ['LMT', 'MKT', 'STP']
            },
            'LSE': {
                'name': 'London Stock Exchange',
                'country_id': 2,  # UK
                'timezone': 'Europe/London',
                'currency': 'GBP',
                'market_open': time(8, 0),
                'market_close': time(16, 30),
                'routing_type': 'DIRECT',
                'smart_routing': False,
                'order_types': ['LMT', 'MKT']
            },
            'TSE': {
                'name': 'Toronto Stock Exchange',
                'country_id': 3,  # Canada
                'timezone': 'America/Toronto',
                'currency': 'CAD',
                'market_open': time(9, 30),
                'market_close': time(16, 0),
                'routing_type': 'DIRECT',
                'smart_routing': False,
                'order_types': ['LMT', 'MKT', 'STP']
            },
            'CME': {
                'name': 'Chicago Mercantile Exchange',
                'country_id': 1,  # USA
                'timezone': 'America/Chicago',
                'currency': 'USD',
                'market_open': time(17, 0),  # Sunday evening start
                'market_close': time(16, 0),  # Friday afternoon end
                'routing_type': 'DIRECT',
                'smart_routing': False,
                'order_types': ['LMT', 'MKT', 'STP', 'MIT']
            },
            'GLOBEX': {
                'name': 'CME Globex',
                'country_id': 1,  # USA
                'timezone': 'America/Chicago',
                'currency': 'USD',
                'market_open': time(17, 0),
                'market_close': time(16, 0),
                'routing_type': 'DIRECT',
                'smart_routing': False,
                'order_types': ['LMT', 'MKT', 'STP', 'MIT']
            },
            'IDEALPRO': {
                'name': 'IBKR Forex Exchange',
                'country_id': 1,  # USA (IBKR primary)
                'timezone': 'America/New_York',
                'currency': 'USD',
                'market_open': time(0, 0),   # 24/7 forex
                'market_close': time(23, 59),
                'routing_type': 'IBKR_FX',
                'smart_routing': True,
                'order_types': ['LMT', 'MKT', 'STP', 'TRAIL']
            }
        }
        
        return ibkr_exchanges.get(exchange_code.upper())

    def get_ibkr_supported_exchanges(self) -> List[Exchange]:
        """Get all exchanges supported by IBKR."""
        supported_codes = [
            'NYSE', 'NASDAQ', 'SMART', 'ARCA', 'LSE', 'TSE', 
            'CME', 'GLOBEX', 'IDEALPRO'
        ]
        
        exchanges = []
        for code in supported_codes:
            exchange = self.get_or_create(code)
            if exchange:
                exchanges.append(exchange)
        
        return exchanges

    def get_smart_routing_exchanges(self) -> List[Exchange]:
        """Get exchanges that support IBKR smart routing."""
        smart_codes = ['SMART', 'IDEALPRO']
        
        exchanges = []
        for code in smart_codes:
            exchange = self.get_or_create(code)
            if exchange:
                exchanges.append(exchange)
        
        return exchanges

    def get_direct_routing_exchanges(self) -> List[Exchange]:
        """Get exchanges that use direct routing."""
        direct_codes = ['NYSE', 'NASDAQ', 'ARCA', 'LSE', 'TSE', 'CME', 'GLOBEX']
        
        exchanges = []
        for code in direct_codes:
            exchange = self.get_or_create(code)
            if exchange:
                exchanges.append(exchange)
        
        return exchanges