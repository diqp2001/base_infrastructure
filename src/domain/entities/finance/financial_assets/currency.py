# domain/entities/financial_assets/currency.py

from .financial_asset import FinancialAsset

class Currency(FinancialAsset):
    """
    Represents a Currency, inheriting properties from FinancialAsset.
    """

    def __init__(self, asset_id: int, name: str, iso_code: str):
        """
        Initialize a Currency object.

        :param asset_id: Unique identifier for the financial asset.
        :param name: Name of the currency (e.g., "US Dollar").
        :param iso_code: ISO 4217 code of the currency (e.g., "USD").
        :param exchange_rate_to_usd: Exchange rate of the currency relative to USD.
        """
        super().__init__(asset_id, name)
        self.iso_code = iso_code

    def __repr__(self):
        return f"Currency(asset_id={self.asset_id}, name={self.name}, iso_code={self.iso_code}, exchange_rate_to_usd={self.exchange_rate_to_usd})"
