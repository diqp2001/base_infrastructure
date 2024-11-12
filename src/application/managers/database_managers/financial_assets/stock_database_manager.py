# src/application/managers/database_managers/financial_assets/stock_database_manager.py

from src.application.managers.database_managers.financial_assets.financial_asset_database_manager import FinancialAssetDatabaseManager
from src.infrastructure.models.financial_assets.stock import Stock

class StockDatabaseManager(FinancialAssetDatabaseManager):
    """
    Stock-specific database manager for handling operations related to the Stock entity.
    """
    def __init__(self, db_type: str = "sqlite"):
        super().__init__(db_type=db_type)

    def get_stock_by_ticker(self, ticker: str):
        """
        Fetch a stock by its ticker symbol.
        """
        try:
            return self.session.query(Stock).filter(Stock.ticker == ticker).first()
        except Exception as e:
            print(f"Error fetching stock by ticker: {e}")
            return None

    def save_stock(self, stock: Stock) -> None:
        """
        Save a stock to the database.
        """
        self.save_asset(stock)

    def get_all_stocks(self):
        """
        Fetch all stocks from the database.
        """
        return self.get_all_assets()
