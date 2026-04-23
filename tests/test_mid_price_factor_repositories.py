"""
tests/test_mid_price_factor_repositories.py

Integration tests for mid-price factor repositories.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal
from datetime import datetime, date

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_mid_price_factor import CompanyShareMidPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_mid_price_factor import CompanyShareOptionMidPriceFactor
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.company_share_mid_price_factor_repository import CompanyShareMidPriceFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.company_share_option_mid_price_factor_repository import CompanyShareOptionMidPriceFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_company_share_mid_price_factor_repository import IBKRCompanyShareMidPriceFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_company_share_option_mid_price_factor_repository import IBKRCompanyShareOptionMidPriceFactorRepository


class TestCompanyShareMidPriceFactorRepository(unittest.TestCase):
    """Test cases for CompanyShareMidPriceFactorRepository."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.mock_factory = Mock()
        self.repository = CompanyShareMidPriceFactorRepository(
            session=self.mock_session,
            factory=self.mock_factory
        )

    def test_repository_initialization(self):
        """Test repository initialization."""
        self.assertEqual(self.repository.session, self.mock_session)
        self.assertEqual(self.repository.factory, self.mock_factory)
        self.assertIsNotNone(self.repository.mapper)

    def test_entity_class_property(self):
        """Test entity_class property."""
        self.assertEqual(self.repository.entity_class, CompanyShareMidPriceFactor)

    def test_model_class_property(self):
        """Test model_class property."""
        from src.infrastructure.models.factor.factor import CompanyShareMidPriceFactorModel
        self.assertEqual(self.repository.model_class, CompanyShareMidPriceFactorModel)

    @patch.object(CompanyShareMidPriceFactorRepository, 'get_by_name')
    def test_create_or_get_existing_factor(self, mock_get_by_name):
        """Test _create_or_get when factor already exists."""
        existing_factor = CompanyShareMidPriceFactor(name="test_factor")
        mock_get_by_name.return_value = existing_factor

        result = self.repository._create_or_get("test_factor")

        self.assertEqual(result, existing_factor)
        mock_get_by_name.assert_called_once_with("test_factor")

    @patch.object(CompanyShareMidPriceFactorRepository, 'get_by_name')
    def test_create_or_get_new_factor(self, mock_get_by_name):
        """Test _create_or_get when creating new factor."""
        mock_get_by_name.return_value = None
        mock_orm_obj = Mock()
        mock_orm_obj.id = 1
        
        # Mock the mapper methods
        self.repository.mapper.to_orm = Mock(return_value=mock_orm_obj)
        self.repository.mapper.to_domain = Mock(
            return_value=CompanyShareMidPriceFactor(factor_id=1, name="new_factor")
        )

        result = self.repository._create_or_get(
            "new_factor",
            group="price",
            subgroup="mid_price_true"
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.name, "new_factor")
        mock_get_by_name.assert_called_once_with("new_factor")
        self.mock_session.add.assert_called_once_with(mock_orm_obj)
        self.mock_session.commit.assert_called_once()


class TestCompanyShareOptionMidPriceFactorRepository(unittest.TestCase):
    """Test cases for CompanyShareOptionMidPriceFactorRepository."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.mock_factory = Mock()
        self.repository = CompanyShareOptionMidPriceFactorRepository(
            session=self.mock_session,
            factory=self.mock_factory
        )

    def test_repository_initialization(self):
        """Test repository initialization."""
        self.assertEqual(self.repository.session, self.mock_session)
        self.assertEqual(self.repository.factory, self.mock_factory)
        self.assertIsNotNone(self.repository.mapper)

    def test_entity_class_property(self):
        """Test entity_class property."""
        self.assertEqual(self.repository.entity_class, CompanyShareOptionMidPriceFactor)

    def test_model_class_property(self):
        """Test model_class property."""
        from src.infrastructure.models.factor.factor import CompanyShareOptionMidPriceFactorModel
        self.assertEqual(self.repository.model_class, CompanyShareOptionMidPriceFactorModel)


class TestIBKRCompanyShareMidPriceFactorRepository(unittest.TestCase):
    """Test cases for IBKRCompanyShareMidPriceFactorRepository."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_ibkr_client = Mock()
        self.mock_factory = Mock()
        self.mock_local_repo = Mock()
        self.mock_factory._local_repositories = {'company_share_mid_price_factor': self.mock_local_repo}
        
        self.repository = IBKRCompanyShareMidPriceFactorRepository(
            ibkr_client=self.mock_ibkr_client,
            factory=self.mock_factory
        )

    def test_repository_initialization(self):
        """Test repository initialization."""
        self.assertEqual(self.repository.ibkr_client, self.mock_ibkr_client)
        self.assertEqual(self.repository.factory, self.mock_factory)
        self.assertEqual(self.repository.local_repo, self.mock_local_repo)

    def test_create_or_get_delegates_to_local(self):
        """Test that _create_or_get delegates to local repository."""
        expected_factor = CompanyShareMidPriceFactor(name="test_factor")
        self.mock_local_repo._create_or_get.return_value = expected_factor

        result = self.repository._create_or_get(
            "test_factor",
            group="price",
            subgroup="mid_price_true"
        )

        self.assertEqual(result, expected_factor)
        self.mock_local_repo._create_or_get.assert_called_once_with(
            name="test_factor",
            group="price",
            subgroup="mid_price_true"
        )

    def test_calculate_mid_price_from_multiple_sources(self):
        """Test calculation of mid price from multiple IBKR sources."""
        # Mock the _gather_ibkr_price_sources method
        sample_prices = [
            {
                'source': 'ibkr_bid',
                'price': Decimal('100.50'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true'
            },
            {
                'source': 'ibkr_ask',
                'price': Decimal('100.70'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true'
            }
        ]
        
        with patch.object(self.repository, '_gather_ibkr_price_sources', return_value=sample_prices):
            result = self.repository.calculate_mid_price_from_multiple_sources("AAPL")
            
            self.assertIsNotNone(result)
            self.assertIsInstance(result, Decimal)
            # Should calculate average: (100.50 + 100.70) / 2 = 100.60
            expected = (Decimal('100.50') + Decimal('100.70')) / 2
            self.assertEqual(result, expected)

    def test_calculate_mid_price_no_sources(self):
        """Test calculation when no price sources are available."""
        with patch.object(self.repository, '_gather_ibkr_price_sources', return_value=[]):
            result = self.repository.calculate_mid_price_from_multiple_sources("INVALID")
            
            self.assertIsNone(result)

    def test_gather_ibkr_price_sources(self):
        """Test gathering price sources from IBKR."""
        # Mock IBKR client methods
        self.mock_ibkr_client.get_market_data.side_effect = [
            {'price': 100.50, 'ask_price': 100.70},  # bid
            {'price': 100.70, 'bid_price': 100.50},  # ask
            {'price': 100.60},  # last
            {'price': 100.55},  # close
        ]

        sources = self.repository._gather_ibkr_price_sources("AAPL")

        self.assertEqual(len(sources), 4)
        self.assertEqual(sources[0]['source'], 'ibkr_bid')
        self.assertEqual(sources[1]['source'], 'ibkr_ask')
        self.assertEqual(sources[2]['source'], 'ibkr_last')
        self.assertEqual(sources[3]['source'], 'ibkr_close')

    def test_get_by_id_delegates_to_local(self):
        """Test that get_by_id delegates to local repository."""
        expected_factor = CompanyShareMidPriceFactor(factor_id=1, name="test_factor")
        self.mock_local_repo.get_by_id.return_value = expected_factor

        result = self.repository.get_by_id(1)

        self.assertEqual(result, expected_factor)
        self.mock_local_repo.get_by_id.assert_called_once_with(1)


class TestIBKRCompanyShareOptionMidPriceFactorRepository(unittest.TestCase):
    """Test cases for IBKRCompanyShareOptionMidPriceFactorRepository."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_ibkr_client = Mock()
        self.mock_factory = Mock()
        self.mock_local_repo = Mock()
        self.mock_factory._local_repositories = {'company_share_option_mid_price_factor': self.mock_local_repo}
        
        self.repository = IBKRCompanyShareOptionMidPriceFactorRepository(
            ibkr_client=self.mock_ibkr_client,
            factory=self.mock_factory
        )

    def test_repository_initialization(self):
        """Test repository initialization."""
        self.assertEqual(self.repository.ibkr_client, self.mock_ibkr_client)
        self.assertEqual(self.repository.factory, self.mock_factory)
        self.assertEqual(self.repository.local_repo, self.mock_local_repo)

    def test_calculate_option_mid_price_from_multiple_sources(self):
        """Test calculation of option mid price from multiple IBKR sources."""
        # Mock the _gather_ibkr_option_price_sources method
        sample_option_prices = [
            {
                'source': 'ibkr_option_bid',
                'price': Decimal('5.50'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true',
                'strike': Decimal('100.00'),
                'expiry': date(2024, 12, 20)
            },
            {
                'source': 'ibkr_option_ask',
                'price': Decimal('5.70'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true',
                'strike': Decimal('100.00'),
                'expiry': date(2024, 12, 20)
            }
        ]
        
        with patch.object(self.repository, '_gather_ibkr_option_price_sources', return_value=sample_option_prices):
            result = self.repository.calculate_option_mid_price_from_multiple_sources(
                "AAPL", 
                Decimal('100.00'), 
                date(2024, 12, 20),
                'C'
            )
            
            self.assertIsNotNone(result)
            self.assertIsInstance(result, Decimal)
            # Should calculate average: (5.50 + 5.70) / 2 = 5.60
            expected = (Decimal('5.50') + Decimal('5.70')) / 2
            self.assertEqual(result, expected)

    def test_gather_ibkr_option_price_sources(self):
        """Test gathering option price sources from IBKR."""
        # Mock IBKR client methods
        mock_contract = Mock()
        self.mock_ibkr_client.create_option_contract.return_value = mock_contract
        self.mock_ibkr_client.get_option_market_data.side_effect = [
            {'price': 5.50, 'ask_price': 5.70},  # bid
            {'price': 5.70, 'bid_price': 5.50},  # ask
            {'price': 5.60},  # last
            {'price': 5.65},  # model
        ]

        sources = self.repository._gather_ibkr_option_price_sources(
            "AAPL", 
            Decimal('100.00'), 
            date(2024, 12, 20),
            'C'
        )

        self.assertEqual(len(sources), 4)
        self.assertEqual(sources[0]['source'], 'ibkr_option_bid')
        self.assertEqual(sources[1]['source'], 'ibkr_option_ask')
        self.assertEqual(sources[2]['source'], 'ibkr_option_last')
        self.assertEqual(sources[3]['source'], 'ibkr_option_model')

        # Verify contract creation was called
        self.mock_ibkr_client.create_option_contract.assert_called_once_with(
            symbol="AAPL",
            expiry=date(2024, 12, 20),
            strike=100.0,
            right='C'
        )


if __name__ == '__main__':
    unittest.main()