from src.infrastructure.repositories.finance.financial_assets.stock_repository import StockRepository
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset

class StockService:
    def __init__(self, repo: StockRepository = None):
        # Dependency Injection: allows easy testing and flexibility
        self.repo = repo or StockRepository()

    def get_stock_by_id(self, id: int) -> FinancialAsset:
        """
        Retrieve a stock by its ID.

        :param id: Stock ID
        :return: FinancialAsset object or None if not found
        """
        stock = self.repo.get_by_id(id)
        if stock is None:
            raise ValueError(f"Stock with id {id} not found.")
        return stock

    def save_stock(self, stock: FinancialAsset) -> None:
        """
        Save a stock to the database.

        :param stock: The Stock object to be saved
        """
        try:
            self.repo.save(stock)
        except Exception as e:
            # You could log the exception here for better debugging in production.
            raise ValueError(f"An error occurred while saving the stock: {e}")
