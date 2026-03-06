"""
Test suite for CompanyShareOption pipeline components.
Tests the creation and functionality of CompanyShareOption entities and their factors.
"""

import unittest
from decimal import Decimal
from datetime import date, datetime

from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import CompanyShareOption
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_price_return_factor import CompanyShareOptionPriceReturnFactor
from src.infrastructure.models.finance.financial_assets.derivative.option.company_share_option import CompanyShareOptionModel
from src.infrastructure.models.factor.factor import CompanyShareOptionFactorModel, CompanyShareOptionPriceReturnFactorModel
from src.infrastructure.repositories.mappers.finance.financial_assets.company_share_option_mapper import CompanyShareOptionMapper
from src.infrastructure.repositories.mappers.factor.company_share_option_price_return_factor_mapper import CompanyShareOptionPriceReturnFactorMapper


class TestCompanyShareOptionDomainEntity(unittest.TestCase):
    """Test the CompanyShareOption domain entity."""

    def test_company_share_option_creation(self):
        """Test creating a CompanyShareOption domain entity."""
        option = CompanyShareOption(
            id=1,
            name="AAPL Call Option",
            symbol="AAPL240315C150",
            currency_id=1,
            underlying_asset_id=100,
            option_type="call",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 15)
        )

        self.assertEqual(option.id, 1)
        self.assertEqual(option.name, "AAPL Call Option")
        self.assertEqual(option.symbol, "AAPL240315C150")
        self.assertEqual(option.currency_id, 1)
        self.assertEqual(option.underlying_asset_id, 100)
        self.assertEqual(option.option_type, "call")
        self.assertEqual(option.start_date, date(2024, 1, 1))
        self.assertEqual(option.end_date, date(2024, 3, 15))


class TestCompanyShareOptionFactor(unittest.TestCase):
    """Test the CompanyShareOptionFactor domain entity."""

    def test_company_share_option_factor_creation(self):
        """Test creating a CompanyShareOptionFactor."""
        factor = CompanyShareOptionFactor(
            name="Test Company Share Option Factor",
            group="Company Share Option Factor",
            subgroup="Test",
            data_type="float",
            source="calculated",
            definition="Test factor for company share options",
            factor_id=1
        )

        self.assertEqual(factor.name, "Test Company Share Option Factor")
        self.assertEqual(factor.group, "Company Share Option Factor")
        self.assertEqual(factor.subgroup, "Test")
        self.assertEqual(factor.data_type, "float")
        self.assertEqual(factor.source, "calculated")
        self.assertEqual(factor.definition, "Test factor for company share options")
        self.assertEqual(factor.factor_id, 1)


class TestCompanyShareOptionPriceReturnFactor(unittest.TestCase):
    """Test the CompanyShareOptionPriceReturnFactor domain entity."""

    def test_company_share_option_price_return_factor_creation(self):
        """Test creating a CompanyShareOptionPriceReturnFactor."""
        factor = CompanyShareOptionPriceReturnFactor(factor_id=1)

        self.assertEqual(factor.name, "Company Share Option Price Return")
        self.assertEqual(factor.group, "Company Share Option Factor")
        self.assertEqual(factor.subgroup, "Price Return")
        self.assertEqual(factor.data_type, "float")
        self.assertEqual(factor.source, "calculated")
        self.assertTrue("price return" in factor.definition.lower())
        self.assertEqual(factor.factor_id, 1)

    def test_calculate_price_return(self):
        """Test price return calculation."""
        factor = CompanyShareOptionPriceReturnFactor()
        
        # Test normal price return calculation
        current_price = 10.0
        previous_price = 8.0
        expected_return = 0.25  # (10 - 8) / 8 = 0.25 or 25%
        
        result = factor.calculate_price_return(current_price, previous_price)
        self.assertAlmostEqual(result, expected_return, places=4)

    def test_calculate_price_return_zero_previous_price(self):
        """Test price return calculation with zero previous price."""
        factor = CompanyShareOptionPriceReturnFactor()
        
        result = factor.calculate_price_return(10.0, 0.0)
        self.assertIsNone(result)

    def test_calculate_log_return(self):
        """Test logarithmic return calculation."""
        factor = CompanyShareOptionPriceReturnFactor()
        
        import math
        current_price = 10.0
        previous_price = 8.0
        expected_log_return = math.log(10.0 / 8.0)
        
        result = factor.calculate_log_return(current_price, previous_price)
        self.assertAlmostEqual(result, expected_log_return, places=4)

    def test_calculate_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        factor = CompanyShareOptionPriceReturnFactor()
        
        option_return = 0.15  # 15% return
        risk_free_rate = 0.03  # 3% risk-free rate
        return_volatility = 0.20  # 20% volatility
        expected_sharpe = (0.15 - 0.03) / 0.20  # 0.6
        
        result = factor.calculate_sharpe_ratio(option_return, risk_free_rate, return_volatility)
        self.assertAlmostEqual(result, expected_sharpe, places=4)


class TestCompanyShareOptionInfrastructure(unittest.TestCase):
    """Test infrastructure models and mappers."""

    def test_company_share_option_model_creation(self):
        """Test creating a CompanyShareOptionModel."""
        model = CompanyShareOptionModel()
        
        # Test that the model can be instantiated
        self.assertIsInstance(model, CompanyShareOptionModel)
        self.assertEqual(model.__tablename__, 'company_share_options')

    def test_company_share_option_mapper(self):
        """Test CompanyShareOption mapper functionality."""
        # Create domain entity
        domain_entity = CompanyShareOption(
            id=1,
            name="Test Option",
            symbol="TEST240315C100",
            currency_id=1,
            underlying_asset_id=100,
            option_type="call",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 15)
        )

        # Convert to ORM
        mapper = CompanyShareOptionMapper()
        orm_model = mapper.to_orm(domain_entity)

        # Verify ORM model
        self.assertIsInstance(orm_model, CompanyShareOptionModel)
        self.assertEqual(orm_model.id, 1)
        self.assertEqual(orm_model.name, "Test Option")
        self.assertEqual(orm_model.symbol, "TEST240315C100")

        # Convert back to domain
        converted_domain = mapper.to_domain(orm_model)
        
        # Verify round-trip conversion
        self.assertEqual(converted_domain.id, domain_entity.id)
        self.assertEqual(converted_domain.name, domain_entity.name)
        self.assertEqual(converted_domain.symbol, domain_entity.symbol)

    def test_factor_model_discriminator(self):
        """Test factor model discriminators are properly set."""
        factor_model = CompanyShareOptionFactorModel()
        price_return_model = CompanyShareOptionPriceReturnFactorModel()
        
        # Check discriminators
        self.assertEqual(factor_model.__mapper_args__['polymorphic_identity'], 'company_share_option_factor')
        self.assertEqual(price_return_model.__mapper_args__['polymorphic_identity'], 'company_share_option_price_return_factor')


if __name__ == '__main__':
    unittest.main()