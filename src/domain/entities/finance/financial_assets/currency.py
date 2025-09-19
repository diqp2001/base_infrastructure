# domain/entities/financial_assets/currency.py

from typing import Optional, Dict, List
from decimal import Decimal
from datetime import datetime

from .financial_asset import FinancialAsset

class CurrencyRate:
    """
    Represents a currency exchange rate at a specific time.
    """
    def __init__(self, rate: Decimal, timestamp: datetime, target_currency: str = "USD"):
        self.rate = rate
        self.timestamp = timestamp
        self.target_currency = target_currency

    def __repr__(self):
        return f"CurrencyRate(rate={self.rate}, target={self.target_currency}, timestamp={self.timestamp.date()})"


class Currency(FinancialAsset):
    """
    Represents a Currency, inheriting properties from FinancialAsset.
    Enhanced with country relationship and exchange rate management.
    """

    def __init__(self, asset_id: int, name: str, iso_code: str, country_id: Optional[int] = None):
        """
        Initialize a Currency object.

        :param asset_id: Unique identifier for the financial asset.
        :param name: Name of the currency (e.g., "US Dollar").
        :param iso_code: ISO 4217 code of the currency (e.g., "USD").
        :param country_id: Optional ID of the country this currency belongs to.
        """
        super().__init__(asset_id, name)
        self.iso_code = iso_code
        self.country_id = country_id
        
        # Exchange rate management
        self.current_rate_to_usd: Optional[Decimal] = None
        self.last_rate_update: Optional[datetime] = None
        self.historical_rates: List[CurrencyRate] = []
        
        # Currency properties
        self.is_major_currency = iso_code in {'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD'}
        self.decimal_places = 0 if iso_code in {'JPY', 'KRW', 'VND'} else 2
        self.is_active = True
        self.is_tradeable = True

    def update_exchange_rate(self, rate: Decimal, timestamp: Optional[datetime] = None, target_currency: str = "USD"):
        """
        Update the current exchange rate for this currency.
        
        :param rate: New exchange rate
        :param timestamp: When the rate was recorded (defaults to now)
        :param target_currency: Target currency (defaults to USD)
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        # Update current rate
        if target_currency == "USD":
            self.current_rate_to_usd = rate
            self.last_rate_update = timestamp
        
        # Store historical rate
        currency_rate = CurrencyRate(rate, timestamp, target_currency)
        self.historical_rates.append(currency_rate)

    def get_rate_at_date(self, date: datetime, target_currency: str = "USD") -> Optional[Decimal]:
        """
        Get the exchange rate closest to the specified date.
        
        :param date: Date to find rate for
        :param target_currency: Target currency
        :return: Exchange rate or None if not found
        """
        applicable_rates = [
            rate for rate in self.historical_rates
            if rate.target_currency == target_currency and rate.timestamp <= date
        ]
        
        if not applicable_rates:
            return None
        
        # Return the most recent rate before or on the specified date
        latest_rate = max(applicable_rates, key=lambda r: r.timestamp)
        return latest_rate.rate

    def add_historical_rates(self, rates_data: List[Dict]):
        """
        Add multiple historical rates from data (e.g., CSV data).
        
        :param rates_data: List of dicts with 'date', 'rate', 'target_currency' keys
        """
        for rate_data in rates_data:
            rate = CurrencyRate(
                rate=Decimal(str(rate_data['rate'])),
                timestamp=rate_data['date'],
                target_currency=rate_data.get('target_currency', 'USD')
            )
            self.historical_rates.append(rate)
        
        # Update current rate to most recent
        if self.historical_rates:
            latest = max(self.historical_rates, key=lambda r: r.timestamp)
            if latest.target_currency == "USD":
                self.current_rate_to_usd = latest.rate
                self.last_rate_update = latest.timestamp

    def get_currency_metrics(self) -> Dict[str, any]:
        """
        Get key metrics for this currency.
        
        :return: Dictionary of currency metrics
        """
        return {
            'iso_code': self.iso_code,
            'name': self.name,
            'country_id': self.country_id,
            'current_rate_usd': float(self.current_rate_to_usd) if self.current_rate_to_usd else None,
            'last_update': self.last_rate_update,
            'is_major': self.is_major_currency,
            'decimal_places': self.decimal_places,
            'historical_data_points': len(self.historical_rates),
            'is_active': self.is_active,
            'is_tradeable': self.is_tradeable
        }

    def __repr__(self):
        return f"Currency(asset_id={self.asset_id}, iso_code={self.iso_code}, name={self.name}, country_id={self.country_id}, rate_usd={self.current_rate_to_usd})"
