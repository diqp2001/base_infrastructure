# src/application/managers/database_managers/financial_assets/financial_asset_database_manager.py

from src.application.managers.database_managers.database_manager import DatabaseManager
from sqlalchemy.orm import Session
from src.infrastructure.models.financial_assets.stock import Stock  # or other asset types

class FinancialAssetDatabaseManager(DatabaseManager):
    """
    Base class for handling database interactions related to financial assets.
    """
    def __init__(self, db_type: str = "sqlite"):
        super().__init__(db_type=db_type)

    def save_asset(self, asset) -> None:
        """
        Save a financial asset (e.g., Stock) to the database.
        """
        try:
            self.session.add(asset)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            print(f"Error saving asset: {e}")

    def get_asset_by_id(self, asset_id: int):
        """
        Fetch a financial asset (e.g., Stock) by its ID.
        """
        try:
            return self.session.query(Stock).filter(Stock.id == asset_id).first()
        except Exception as e:
            print(f"Error fetching asset: {e}")
            return None

    def get_all_assets(self):
        """
        Fetch all financial assets (e.g., all Stocks) from the database.
        """
        try:
            return self.session.query(Stock).all()
        except Exception as e:
            print(f"Error fetching assets: {e}")
            return []
