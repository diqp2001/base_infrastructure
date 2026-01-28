"""
IBKR Crypto Repository - Interactive Brokers implementation for Cryptocurrencies.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.domain.ports.finance.financial_assets.crypto_port import CryptoPort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import IBKRFinancialAssetRepository
from src.domain.entities.finance.financial_assets.crypto import Crypto


class IBKRCryptoRepository(IBKRFinancialAssetRepository, CryptoPort):
    """
    IBKR implementation of CryptoPort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory):
        """
        Initialize IBKR Crypto Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client (InteractiveBrokersBroker instance)
            factory: Repository factory for dependency injection (preferred)
        """
        self.ib_broker = ibkr_client  # Use ib_broker for consistency with reference implementation
        
        self.factory = factory
        self.local_repo = self.factory.crypto_local_repo
    @property
    def entity_class(self):
        """Return the domain entity class for Crypto."""
        return Crypto
    def _create_or_get(self, symbol: str) -> Optional[Crypto]:
        """
        Get or create a cryptocurrency by symbol using IBKR API.
        
        Args:
            symbol: The crypto symbol (e.g., 'BTC', 'ETH', 'BTCUSD')
            
        Returns:
            Crypto entity or None if creation/retrieval failed
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
            entity = self._contract_to_domain(contract, contract_details_list, symbol)
            if not entity:
                return None
                
            # 5. Delegate persistence to local repository
            return self.local_repo.add(entity)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for crypto symbol {symbol}: {e}")
            return None

    def get_by_symbol(self, symbol: str) -> Optional[Crypto]:
        """Get crypto by symbol (delegates to local repository)."""
        return self.local_repo.get_by_symbol(symbol)

    def get_by_id(self, entity_id: int) -> Optional[Crypto]:
        """Get crypto by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Crypto]:
        """Get all cryptocurrencies (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Crypto) -> Optional[Crypto]:
        """Add crypto entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Crypto) -> Optional[Crypto]:
        """Update crypto entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete crypto entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def _fetch_contract(self, symbol: str) -> Optional[Contract]:
        """
        Fetch cryptocurrency contract from IBKR API.
        
        Args:
            symbol: Crypto symbol
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            
            # IBKR typically handles crypto as CRYPTO secType
            contract.secType = "CRYPTO"
            
            # Parse symbol to determine base and quote currencies
            base_crypto, quote_currency = self._parse_crypto_symbol(symbol)
            
            contract.symbol = base_crypto
            contract.currency = quote_currency
            contract.exchange = "PAXOS"  # IBKR's crypto exchange
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR crypto contract for {symbol}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[List[dict]]:
        """
        Fetch crypto contract details from IBKR API using broker method.
        
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
            print(f"Error fetching IBKR crypto contract details: {e}")
            return None

    def _contract_to_domain(self, contract: Contract, contract_details_list: List[dict], original_symbol: str) -> Optional[Crypto]:
        """
        Convert IBKR contract and details to domain entity using real API data.
        
        Args:
            contract: IBKR Contract object
            contract_details_list: List of contract details dictionaries from IBKR API
            original_symbol: Original symbol provided
            
        Returns:
            Crypto domain entity or None if conversion failed
        """
        try:
            # Use the first contract details result
            contract_details = contract_details_list[0] if contract_details_list else {}
            
            crypto_info = self._get_crypto_info(contract.symbol)
            
            return Crypto(
                id=None,  # Let database generate
                symbol=original_symbol,
                name=crypto_info['name'],
                base_currency=contract.symbol,
                quote_currency=contract.currency,
                blockchain_network=crypto_info['blockchain'],
                total_supply=crypto_info.get('total_supply'),
                circulating_supply=crypto_info.get('circulating_supply'),
                market_cap=None,  # Would need real-time data
                # IBKR-specific fields
                ibkr_contract_id=getattr(contract, 'conId', None),
                ibkr_local_symbol=getattr(contract, 'localSymbol', ''),
                ibkr_exchange=contract.exchange,
                ibkr_min_tick=Decimal(str(contract_details.get('min_tick', 0.01))),
                ibkr_underlying_symbol=contract_details.get('underlying_symbol', '')
            )
        except Exception as e:
            print(f"Error converting IBKR crypto contract to domain entity: {e}")
            return None

    def _parse_crypto_symbol(self, symbol: str) -> tuple[str, str]:
        """
        Parse cryptocurrency symbol into base and quote currencies.
        
        Args:
            symbol: Crypto symbol (e.g., 'BTCUSD', 'ETHUSD', 'BTC')
            
        Returns:
            Tuple of (base_crypto, quote_currency)
        """
        # Common crypto symbols
        crypto_symbols = {
            'BTC', 'ETH', 'LTC', 'BCH', 'XRP', 'ADA', 'DOT', 'LINK',
            'BNB', 'SOL', 'AVAX', 'MATIC', 'UNI', 'ATOM', 'ALGO',
            'XLM', 'VET', 'ICP', 'FIL', 'THETA', 'AAVE', 'MKR'
        }
        
        # If it's just a crypto symbol, assume USD pairing
        if symbol.upper() in crypto_symbols:
            return symbol.upper(), 'USD'
        
        # Try to parse combined symbol
        for crypto in crypto_symbols:
            if symbol.upper().startswith(crypto):
                remainder = symbol[len(crypto):].upper()
                if remainder in ['USD', 'EUR', 'GBP', 'JPY']:
                    return crypto, remainder
        
        # Default fallback
        if len(symbol) > 3:
            return symbol[:3].upper(), symbol[3:].upper()
        else:
            return symbol.upper(), 'USD'

    def _get_crypto_info(self, crypto_symbol: str) -> dict:
        """Get cryptocurrency information."""
        crypto_data = {
            'BTC': {
                'name': 'Bitcoin',
                'blockchain': 'Bitcoin',
                'min_tick': 0.01,
                'total_supply': 21000000,
                'circulating_supply': 19500000
            },
            'ETH': {
                'name': 'Ethereum',
                'blockchain': 'Ethereum',
                'min_tick': 0.01,
                'total_supply': None,  # No cap
                'circulating_supply': 120000000
            },
            'LTC': {
                'name': 'Litecoin',
                'blockchain': 'Litecoin',
                'min_tick': 0.01,
                'total_supply': 84000000,
                'circulating_supply': 73000000
            },
            'BCH': {
                'name': 'Bitcoin Cash',
                'blockchain': 'Bitcoin Cash',
                'min_tick': 0.01,
                'total_supply': 21000000,
                'circulating_supply': 19600000
            },
            'XRP': {
                'name': 'Ripple',
                'blockchain': 'XRP Ledger',
                'min_tick': 0.0001,
                'total_supply': 100000000000,
                'circulating_supply': 50000000000
            },
            'ADA': {
                'name': 'Cardano',
                'blockchain': 'Cardano',
                'min_tick': 0.0001,
                'total_supply': 45000000000,
                'circulating_supply': 35000000000
            },
            'DOT': {
                'name': 'Polkadot',
                'blockchain': 'Polkadot',
                'min_tick': 0.01,
                'total_supply': 1100000000,
                'circulating_supply': 1000000000
            },
            'LINK': {
                'name': 'Chainlink',
                'blockchain': 'Ethereum',
                'min_tick': 0.001,
                'total_supply': 1000000000,
                'circulating_supply': 500000000
            }
        }
        
        return crypto_data.get(crypto_symbol, {
            'name': f'{crypto_symbol} Token',
            'blockchain': 'Unknown',
            'min_tick': 0.01,
            'total_supply': None,
            'circulating_supply': None
        })

    def get_major_cryptocurrencies(self) -> List[Crypto]:
        """Get major cryptocurrencies available on IBKR."""
        major_cryptos = ['BTCUSD', 'ETHUSD', 'LTCUSD', 'BCHUSD']
        
        cryptos = []
        for symbol in major_cryptos:
            crypto = self.get_or_create(symbol)
            if crypto:
                cryptos.append(crypto)
        
        return cryptos

    def get_defi_tokens(self) -> List[Crypto]:
        """Get DeFi tokens available on IBKR."""
        defi_tokens = ['LINKUSD', 'UNIUSD', 'AAVEUSD', 'MKRUSD']
        
        cryptos = []
        for symbol in defi_tokens:
            crypto = self.get_or_create(symbol)
            if crypto:
                cryptos.append(crypto)
        
        return cryptos

    def get_crypto_by_blockchain(self, blockchain: str) -> List[Crypto]:
        """Get cryptocurrencies by blockchain network."""
        # This would delegate to local repository for filtering
        return self.local_repo.get_crypto_by_blockchain(blockchain)

    def is_supported_by_ibkr(self, symbol: str) -> bool:
        """Check if cryptocurrency is supported by IBKR."""
        # IBKR supports a limited set of cryptocurrencies
        supported_cryptos = [
            'BTC', 'ETH', 'LTC', 'BCH', 'LINK', 'UNI', 'AAVE', 'MKR'
        ]
        
        base_crypto, _ = self._parse_crypto_symbol(symbol)
        return base_crypto in supported_cryptos