"""
Comprehensive test suite for PortfolioCompanyShareOption pipeline components.

Tests domain entities, infrastructure models, repositories, mappers, and integrations
following the same pattern as CompanyShareOption tests.
"""

import unittest
from unittest.mock import Mock, patch
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Domain imports
from src.domain.entities.finance.financial_assets.derivatives.option.portfolio_company_share_option import PortfolioCompanyShareOption
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_price_return_factor import PortfolioCompanyShareOptionPriceReturnFactor

# Infrastructure imports
from src.infrastructure.models.finance.portfolio.portfolio_company_share_option import CompanyShareOptionPortfolioModel
from src.infrastructure.models import ModelBase
from infrastructure.repositories.local_repo.finance.financial_assets.derivatives.option.portfolio_company_share_option_repository import PortfolioCompanyShareOptionRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.portfolio_company_share_option_price_return_factor_repository import PortfolioCompanyShareOptionPriceReturnFactorRepository
from infrastructure.repositories.mappers.finance.financial_assets.portfolio_company_share_option_mapper import PortfolioCompanyShareOptionMapper
from src.infrastructure.repositories.mappers.factor.portfolio_company_share_option_price_return_factor_mapper import PortfolioCompanyShareOptionPriceReturnFactorMapper
from src.infrastructure.repositories.repository_factory import RepositoryFactory


class TestPortfolioCompanyShareOptionDomainEntity(unittest.TestCase):
    """Test PortfolioCompanyShareOption domain entity functionality."""
    
    def test_create_portfolio_company_share_option_entity(self):
        """Test creating a PortfolioCompanyShareOption domain entity."""
        option = PortfolioCompanyShareOption(
            id=1,
            name="AAPL Portfolio Option Call",
            symbol="AAPL_PF_C_150_2024",
            currency_id=1,
            underlying_asset_id=100,
            option_type="CALL",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        
        self.assertEqual(option.id, 1)
        self.assertEqual(option.name, "AAPL Portfolio Option Call")
        self.assertEqual(option.symbol, "AAPL_PF_C_150_2024")
        self.assertEqual(option.currency_id, 1)
        self.assertEqual(option.underlying_asset_id, 100)
        self.assertEqual(option.option_type, "CALL")
        self.assertEqual(option.start_date, date(2024, 1, 1))
        self.assertEqual(option.end_date, date(2024, 12, 31))
    
    def test_portfolio_company_share_option_optional_fields(self):
        """Test creating PortfolioCompanyShareOption with optional fields."""
        option = PortfolioCompanyShareOption(
            id=None,
            name="Test Option",
            symbol=None
        )
        
        self.assertIsNone(option.id)
        self.assertEqual(option.name, "Test Option")
        self.assertIsNone(option.symbol)
        self.assertIsNone(option.currency_id)
        self.assertIsNone(option.underlying_asset_id)


class TestPortfolioCompanyShareOptionPriceReturnFactor(unittest.TestCase):
    """Test PortfolioCompanyShareOptionPriceReturnFactor domain entity functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.factor = PortfolioCompanyShareOptionPriceReturnFactor(factor_id=1)
    
    def test_create_price_return_factor(self):
        """Test creating a PortfolioCompanyShareOptionPriceReturnFactor."""
        self.assertEqual(self.factor.name, "Portfolio Company Share Option Price Return")
        self.assertEqual(self.factor.group, "Portfolio Company Share Option Factor")
        self.assertEqual(self.factor.subgroup, "Price Return")
        self.assertEqual(self.factor.data_type, "float")
        self.assertEqual(self.factor.source, "calculated")
        self.assertIn("Price return", self.factor.definition)
    
    def test_calculate_price_return(self):
        """Test price return calculation."""
        # Normal case
        result = self.factor.calculate_price_return(110.0, 100.0)
        self.assertEqual(result, 0.1)  # 10% return
        
        # Negative return
        result = self.factor.calculate_price_return(90.0, 100.0)
        self.assertEqual(result, -0.1)  # -10% return
        
        # Zero previous price (edge case)
        result = self.factor.calculate_price_return(110.0, 0.0)
        self.assertIsNone(result)
        
        # Negative previous price (edge case)
        result = self.factor.calculate_price_return(110.0, -10.0)
        self.assertIsNone(result)
    
    def test_calculate_log_return(self):
        """Test logarithmic return calculation."""
        import math
        
        # Normal case
        result = self.factor.calculate_log_return(110.0, 100.0)
        expected = math.log(110.0 / 100.0)
        self.assertAlmostEqual(result, expected, places=6)
        
        # Zero current price (edge case)
        result = self.factor.calculate_log_return(0.0, 100.0)
        self.assertIsNone(result)
        
        # Zero previous price (edge case)
        result = self.factor.calculate_log_return(110.0, 0.0)
        self.assertIsNone(result)
    
    def test_calculate_volatility_adjusted_return(self):
        """Test volatility-adjusted return calculation."""
        # Normal case
        result = self.factor.calculate_volatility_adjusted_return(110.0, 100.0, 0.2, 1.0)
        expected = 0.1 / 0.2  # (10% return) / 20% volatility
        self.assertEqual(result, expected)
        
        # Zero volatility (edge case)
        result = self.factor.calculate_volatility_adjusted_return(110.0, 100.0, 0.0, 1.0)
        self.assertIsNone(result)
        
        # Zero previous price (edge case)
        result = self.factor.calculate_volatility_adjusted_return(110.0, 0.0, 0.2, 1.0)
        self.assertIsNone(result)
    
    def test_calculate_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        # Normal case
        result = self.factor.calculate_sharpe_ratio(0.12, 0.02, 0.15)
        expected = (0.12 - 0.02) / 0.15
        self.assertAlmostEqual(result, expected, places=6)
        
        # Zero volatility (edge case)
        result = self.factor.calculate_sharpe_ratio(0.12, 0.02, 0.0)
        self.assertIsNone(result)
    
    def test_calculate_underlying_correlation_return(self):
        """Test underlying correlation return calculation."""
        # Normal case
        result = self.factor.calculate_underlying_correlation_return(0.15, 0.10)
        self.assertEqual(result, 1.5)  # Option moved 1.5x underlying
        
        # Zero underlying return (edge case)
        result = self.factor.calculate_underlying_correlation_return(0.15, 0.0)
        self.assertIsNone(result)
    
    def test_calculate_portfolio_weighted_return(self):
        """Test portfolio-weighted return calculation."""
        portfolio_weights = {"AAPL": 0.6, "MSFT": 0.4}
        portfolio_returns = {"AAPL": 0.10, "MSFT": 0.05}
        
        # Normal case
        result = self.factor.calculate_portfolio_weighted_return(0.16, portfolio_weights, portfolio_returns)
        expected_portfolio_return = 0.6 * 0.10 + 0.4 * 0.05  # 0.08
        expected_sensitivity = 0.16 / expected_portfolio_return  # 2.0
        self.assertEqual(result, expected_sensitivity)
        
        # Empty weights/returns (edge case)
        result = self.factor.calculate_portfolio_weighted_return(0.16, {}, {})
        self.assertIsNone(result)


class TestPortfolioCompanyShareOptionInfrastructure(unittest.TestCase):
    """Test PortfolioCompanyShareOption infrastructure layer."""
    
    def setUp(self):
        """Set up test database."""
        # Create in-memory SQLite database for testing
        self.engine = create_engine("sqlite:///:memory:")
        ModelBase.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.factory = RepositoryFactory(self.session)
    
    def tearDown(self):
        """Clean up test database."""
        self.session.close()
    
    def test_portfolio_company_share_option_model_creation(self):
        """Test creating PortfolioCompanyShareOptionModel."""
        model = CompanyShareOptionPortfolioModel(
            name="Test Portfolio Option",
            symbol="TEST_PF_OPT",
            option_type="CALL"
        )
        
        self.assertEqual(model.symbol, "TEST_PF_OPT")
        self.assertEqual(model.option_type, "CALL")
        self.assertEqual(model.__mapper_args__["polymorphic_identity"], "portfolio_company_share_option")
    
    def test_portfolio_company_share_option_repository_creation(self):
        """Test creating PortfolioCompanyShareOptionRepository."""
        repo = PortfolioCompanyShareOptionRepository(self.session, factory=self.factory)
        
        self.assertEqual(repo.model_class, CompanyShareOptionPortfolioModel)
        self.assertEqual(repo.entity_class, PortfolioCompanyShareOption)
        self.assertIsInstance(repo.mapper, PortfolioCompanyShareOptionMapper)
    
    def test_portfolio_company_share_option_price_return_factor_repository_creation(self):
        """Test creating PortfolioCompanyShareOptionPriceReturnFactorRepository."""
        repo = PortfolioCompanyShareOptionPriceReturnFactorRepository(self.session, factory=self.factory)
        
        self.assertEqual(repo.entity_class, PortfolioCompanyShareOptionPriceReturnFactor)
        self.assertIsInstance(repo.mapper, PortfolioCompanyShareOptionPriceReturnFactorMapper)


class TestPortfolioCompanyShareOptionMappers(unittest.TestCase):
    """Test mapper functionality for PortfolioCompanyShareOption entities."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.option_mapper = PortfolioCompanyShareOptionMapper()
        self.factor_mapper = PortfolioCompanyShareOptionPriceReturnFactorMapper()
    
    def test_portfolio_company_share_option_mapper_to_entity(self):
        """Test mapping from model to domain entity."""
        model = CompanyShareOptionPortfolioModel(
            id=1,
            name="Test Portfolio Option",
            symbol="TEST_PF_OPT",
            option_type="CALL",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        
        entity = self.option_mapper.to_entity(model)
        
        self.assertIsInstance(entity, PortfolioCompanyShareOption)
        self.assertEqual(entity.id, 1)
        self.assertEqual(entity.name, "Test Portfolio Option")
        self.assertEqual(entity.symbol, "TEST_PF_OPT")
        self.assertEqual(entity.option_type, "CALL")
        self.assertEqual(entity.start_date, date(2024, 1, 1))
        self.assertEqual(entity.end_date, date(2024, 12, 31))
    
    def test_portfolio_company_share_option_mapper_to_model(self):
        """Test mapping from domain entity to model."""
        entity = PortfolioCompanyShareOption(
            id=1,
            name="Test Portfolio Option",
            symbol="TEST_PF_OPT",
            option_type="CALL",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        
        model = self.option_mapper.to_model(entity)
        
        self.assertIsInstance(model, CompanyShareOptionPortfolioModel)
        self.assertEqual(model.id, 1)
        self.assertEqual(model.name, "Test Portfolio Option")
        self.assertEqual(model.symbol, "TEST_PF_OPT")
        self.assertEqual(model.option_type, "CALL")
        self.assertEqual(model.start_date, date(2024, 1, 1))
        self.assertEqual(model.end_date, date(2024, 12, 31))
    
    def test_portfolio_company_share_option_mapper_round_trip(self):
        """Test round-trip conversion: entity -> model -> entity."""
        original_entity = PortfolioCompanyShareOption(
            id=42,
            name="Round Trip Test",
            symbol="RT_TEST",
            currency_id=1,
            underlying_asset_id=100,
            option_type="PUT",
            start_date=date(2024, 1, 1),
            end_date=None
        )
        
        # Convert to model and back
        model = self.option_mapper.to_model(original_entity)
        converted_entity = self.option_mapper.to_entity(model)
        
        # Verify all fields match
        self.assertEqual(converted_entity.id, original_entity.id)
        self.assertEqual(converted_entity.name, original_entity.name)
        self.assertEqual(converted_entity.symbol, original_entity.symbol)
        self.assertEqual(converted_entity.currency_id, original_entity.currency_id)
        self.assertEqual(converted_entity.underlying_asset_id, original_entity.underlying_asset_id)
        self.assertEqual(converted_entity.option_type, original_entity.option_type)
        self.assertEqual(converted_entity.start_date, original_entity.start_date)
        self.assertEqual(converted_entity.end_date, original_entity.end_date)


class TestPortfolioCompanyShareOptionFactorMappers(unittest.TestCase):
    """Test factor mapper functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mapper = PortfolioCompanyShareOptionPriceReturnFactorMapper()
    
    def test_factor_mapper_to_entity(self):
        """Test mapping factor from model to domain entity."""
        from src.infrastructure.models.factor.factor import PortfolioCompanyShareOptionPriceReturnFactorModel
        
        model = PortfolioCompanyShareOptionPriceReturnFactorModel(
            id=1,
            name="Portfolio Company Share Option Price Return",
            group="Portfolio Company Share Option Factor",
            subgroup="Price Return",
            data_type="float",
            source="calculated"
        )
        
        entity = self.mapper.to_entity(model)
        
        self.assertIsInstance(entity, PortfolioCompanyShareOptionPriceReturnFactor)
        self.assertEqual(entity.name, "Portfolio Company Share Option Price Return")
        self.assertEqual(entity.group, "Portfolio Company Share Option Factor")
        self.assertEqual(entity.subgroup, "Price Return")


class TestPortfolioCompanyShareOptionIntegration(unittest.TestCase):
    """Integration tests for PortfolioCompanyShareOption pipeline."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.engine = create_engine("sqlite:///:memory:")
        ModelBase.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.factory = RepositoryFactory(self.session)
    
    def tearDown(self):
        """Clean up integration test environment."""
        self.session.close()
    
    def test_repository_factory_integration(self):
        """Test that PortfolioCompanyShareOption repositories are properly registered."""
        # Test main entity repository
        option_repo = self.factory._local_repositories.get('portfolio_company_share_option')
        self.assertIsNotNone(option_repo)
        self.assertIsInstance(option_repo, PortfolioCompanyShareOptionRepository)
        
        # Test factor repositories
        price_return_factor_repo = self.factory._local_repositories.get('portfolio_company_share_option_price_return_factor')
        self.assertIsNotNone(price_return_factor_repo)
        self.assertIsInstance(price_return_factor_repo, PortfolioCompanyShareOptionPriceReturnFactorRepository)
        
        delta_factor_repo = self.factory._local_repositories.get('portfolio_company_share_option_delta_factor')
        self.assertIsNotNone(delta_factor_repo)
        
        price_factor_repo = self.factory._local_repositories.get('portfolio_company_share_option_price_factor')
        self.assertIsNotNone(price_factor_repo)
    
    @patch('src.infrastructure.repositories.local_repo.finance.financial_assets.currency_repository.CurrencyRepository')
    @patch('src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository.CompanyShareRepository')
    def test_get_or_create_portfolio_company_share_option(self, mock_share_repo, mock_currency_repo):
        """Test get_or_create functionality for PortfolioCompanyShareOption."""
        # Mock dependencies
        mock_currency = Mock()
        mock_currency.id = 1
        mock_currency_repo.get_or_create.return_value = mock_currency
        
        mock_share = Mock()
        mock_share.id = 100
        mock_share_repo.get_or_create.return_value = mock_share
        
        # Get repository
        repo = self.factory._local_repositories['portfolio_company_share_option']
        
        # Test creation
        option = repo.get_or_create(
            name="Test Portfolio Option",
            symbol="TEST_PF",
            option_type="CALL"
        )
        
        self.assertIsNotNone(option)
        self.assertEqual(option.name, "Test Portfolio Option")
        self.assertEqual(option.symbol, "TEST_PF")


if __name__ == '__main__':
    unittest.main()