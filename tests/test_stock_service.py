import unittest
from unittest.mock import MagicMock
from src.application.services.financial_assets.stock import StockService
from src.domain.entities.financial_assets.financial_asset import FinancialAsset

class TestStockService(unittest.TestCase):

    def setUp(self):
        # Create a mock repository
        self.mock_repo = MagicMock()
        # Initialize StockService with the mocked repository
        self.stock_service = StockService(repo=self.mock_repo)

    def test_get_stock_by_id_found(self):
        # Mock the repository method to return a FinancialAsset object
        stock = FinancialAsset(name="Test Stock", ticker="TEST", value=100.0, date="2024-11-01")
        self.mock_repo.get_by_id.return_value = stock

        # Call the service method
        result = self.stock_service.get_stock_by_id(1)

        # Check if the returned result is as expected
        self.assertEqual(result, stock)
        self.mock_repo.get_by_id.assert_called_once_with(1)  # Ensure repository method was called with correct argument

    def test_get_stock_by_id_not_found(self):
        # Mock the repository method to return None (not found)
        self.mock_repo.get_by_id.return_value = None

        # Call the service method and check for ValueError exception
        with self.assertRaises(ValueError):
            self.stock_service.get_stock_by_id(1)

    def test_save_stock(self):
        # Create a mock stock instance
        stock = FinancialAsset(name="Test Stock", ticker="TEST", value=100.0, date="2024-11-01")

        # Mock the repository save method
        self.mock_repo.save.return_value = None

        # Call the service method
        self.stock_service.save_stock(stock)

        # Ensure the save method was called with the correct stock
        self.mock_repo.save.assert_called_once_with(stock)

    def test_save_stock_error_handling(self):
        # Create a mock stock instance
        stock = FinancialAsset(name="Test Stock", ticker="TEST", value=100.0, date="2024-11-01")

        # Simulate an error in the repository's save method
        self.mock_repo.save.side_effect = Exception("Database error")

        # Call the service method and ensure that the exception is raised
        with self.assertRaises(ValueError):
            self.stock_service.save_stock(stock)

if __name__ == '__main__':
    unittest.main()