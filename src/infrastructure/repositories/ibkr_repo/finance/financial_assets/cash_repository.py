"""
IBKR Cash Repository - Interactive Brokers implementation for Cash positions.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails
from ibapi.common import TickerId

from src.domain.ports.finance.financial_assets.cash_port import CashPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_repository import BaseIBKRRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_base_repository import FinancialAssetBaseRepository
from src.domain.entities.finance.financial_assets.cash import Cash


class IBKRCashRepository(FinancialAssetBaseRepository, CashPort):
    """
    IBKR implementation of CashPort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, local_repo: CashPort):
        """
        Initialize IBKR Cash Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            local_repo: Local repository implementing CashPort for persistence
        """
        self.ibkr = ibkr_client
        self.local_repo = local_repo

    def get_or_create(self, currency_code: str) -> Optional[Cash]:
        """
        Get or create a cash position by currency using IBKR API.
        
        Args:
            currency_code: The currency code (e.g., 'USD', 'EUR', 'GBP')
            
        Returns:
            Cash entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            existing = self.local_repo.get_by_currency(currency_code)
            if existing:
                return existing
            
            # 2. For cash, we don't need to fetch from IBKR API as it's a simple entity
            # We can create it directly with IBKR-specific metadata
            entity = self._create_cash_entity(currency_code)
            if not entity:
                return None
                
            # 3. Delegate persistence to local repository
            return self.local_repo.add(entity)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for cash currency {currency_code}: {e}")
            return None

    def get_by_currency(self, currency_code: str) -> Optional[Cash]:
        """Get cash by currency (delegates to local repository)."""
        return self.local_repo.get_by_currency(currency_code)

    def get_by_id(self, entity_id: int) -> Optional[Cash]:
        """Get cash by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Cash]:
        """Get all cash positions (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Cash) -> Optional[Cash]:
        """Add cash entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Cash) -> Optional[Cash]:
        """Update cash entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete cash entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def get_account_cash_balances(self, account_id: str) -> List[Cash]:
        """
        Get cash balances for a specific IBKR account.
        This would fetch actual cash positions from IBKR API.
        
        Args:
            account_id: IBKR account identifier
            
        Returns:
            List of Cash entities representing account balances
        """
        try:
            # In real implementation, would use:
            # self.ibkr.reqAccountSummary() to get cash balances
            
            # Mock implementation showing different currencies
            cash_balances = []
            mock_balances = {
                'USD': Decimal('10000.00'),
                'EUR': Decimal('5000.00'),
                'GBP': Decimal('3000.00')
            }
            
            for currency, balance in mock_balances.items():
                cash = self.get_or_create(currency)
                if cash:
                    # Update with actual balance from IBKR
                    cash.current_balance = balance
                    cash_balances.append(cash)
            
            return cash_balances
            
        except Exception as e:
            print(f"Error fetching IBKR cash balances for account {account_id}: {e}")
            return []

    def _create_cash_entity(self, currency_code: str) -> Optional[Cash]:
        """
        Create a cash entity with IBKR-specific properties.
        
        Args:
            currency_code: Currency code (e.g., 'USD', 'EUR')
            
        Returns:
            Cash domain entity or None if creation failed
        """
        try:
            # Validate currency code
            if not self._is_valid_currency_code(currency_code):
                raise ValueError(f"Invalid currency code: {currency_code}")
            
            return Cash(
                id=None,  # Let database generate
                currency_code=currency_code.upper(),
                name=f"{currency_code.upper()} Cash",
                current_balance=Decimal('0.00'),  # Default balance
                available_balance=Decimal('0.00'),  # Available for trading
                interest_rate=self._get_default_interest_rate(currency_code),
                # IBKR-specific fields
                ibkr_currency_code=currency_code.upper(),
                ibkr_account_type="CASH",  # vs "MARGIN"
                ibkr_settlement_currency=currency_code.upper(),
                ibkr_buying_power_multiplier=Decimal('1.0')  # Cash accounts have 1x buying power
            )
        except Exception as e:
            print(f"Error creating cash entity for {currency_code}: {e}")
            return None

    def _is_valid_currency_code(self, currency_code: str) -> bool:
        """Validate currency code against IBKR supported currencies."""
        supported_currencies = {
            'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNH',
            'CZK', 'DKK', 'HKD', 'HUF', 'ILS', 'KRW', 'MXN', 'NOK',
            'NZD', 'PLN', 'RUB', 'SEK', 'SGD', 'TRY', 'ZAR', 'INR'
        }
        return currency_code.upper() in supported_currencies

    def _get_default_interest_rate(self, currency_code: str) -> Decimal:
        """Get default interest rates for different currencies (mock data)."""
        default_rates = {
            'USD': Decimal('5.25'),   # Fed funds rate
            'EUR': Decimal('4.50'),   # ECB rate
            'GBP': Decimal('5.25'),   # BoE rate
            'JPY': Decimal('0.10'),   # BoJ rate
            'AUD': Decimal('4.35'),   # RBA rate
            'CAD': Decimal('4.75'),   # BoC rate
            'CHF': Decimal('1.75'),   # SNB rate
        }
        return default_rates.get(currency_code.upper(), Decimal('0.00'))

    def get_supported_currencies(self) -> List[str]:
        """Get list of currencies supported by IBKR."""
        return [
            'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNH',
            'CZK', 'DKK', 'HKD', 'HUF', 'ILS', 'KRW', 'MXN', 'NOK',
            'NZD', 'PLN', 'RUB', 'SEK', 'SGD', 'TRY', 'ZAR', 'INR'
        ]

    def create_multi_currency_cash_positions(self, currencies: List[str]) -> List[Cash]:
        """Create cash positions for multiple currencies."""
        cash_positions = []
        
        for currency in currencies:
            if self._is_valid_currency_code(currency):
                cash = self.get_or_create(currency)
                if cash:
                    cash_positions.append(cash)
            else:
                print(f"Warning: Unsupported currency {currency}")
        
        return cash_positions