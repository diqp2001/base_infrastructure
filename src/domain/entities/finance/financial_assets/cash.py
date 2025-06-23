# domain/entities/financial_assets/cash.py

from .financial_asset import FinancialAsset

class Cash(FinancialAsset):
    """
    Represents Cash, inheriting properties from FinancialAsset.
    """

    def __init__(self, asset_id: int, name: str, amount: float, currency: str):
        """
        Initialize a Cash object.

        :param asset_id: Unique identifier for the financial asset.
        :param name: Name of the cash asset (e.g., "Cash on Hand").
        :param amount: The total amount of cash available.
        :param currency: The currency in which the cash is denominated.
        """
        super().__init__(asset_id, name)
        self.amount = amount
        self.currency = currency

    def __repr__(self):
        return f"Cash(asset_id={self.asset_id}, name={self.name}, amount={self.amount}, currency={self.currency})"
