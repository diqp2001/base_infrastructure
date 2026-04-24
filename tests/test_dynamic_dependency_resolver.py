"""
tests/test_dynamic_dependency_resolver.py

Test suite for dynamic dependency resolution system.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from decimal import Decimal

from src.domain.entities.factor.dynamic_dependency_requirements import DependencyRequirements
from src.application.services.factor.dynamic_dependency_resolver import DynamicDependencyResolver
from src.domain.entities.factor.factor_value import FactorValue


class TestDynamicDependencyRequirements(unittest.TestCase):
    """Test cases for DependencyRequirements domain entity."""

    def setUp(self):
        """Set up test fixtures."""
        self.basic_requirements = DependencyRequirements(
            required_groups=["price"],
            min_sources=2
        )

    def test_basic_requirements_creation(self):
        """Test creating basic dependency requirements."""
        self.assertEqual(self.basic_requirements.required_groups, ["price"])
        self.assertEqual(self.basic_requirements.min_sources, 2)
        self.assertEqual(self.basic_requirements.max_age_days, 1)

    def test_requirements_validation(self):
        """Test validation of dependency requirements."""
        # Test empty required_groups raises error
        with self.assertRaises(ValueError):
            DependencyRequirements(required_groups=[])
        
        # Test negative min_sources raises error
        with self.assertRaises(ValueError):
            DependencyRequirements(required_groups=["price"], min_sources=0)
        
        # Test max_sources < min_sources raises error
        with self.assertRaises(ValueError):
            DependencyRequirements(
                required_groups=["price"], 
                min_sources=3, 
                max_sources=2
            )

    def test_factor_matching(self):
        """Test factor matching logic."""
        # Create mock factor
        mock_factor = Mock()
        mock_factor.group = "price"
        mock_factor.subgroup = "close"
        mock_factor.source = "ibkr"
        
        requirements = DependencyRequirements(
            required_groups=["price"],
            required_subgroups=["close", "mid_price"]
        )
        
        self.assertTrue(requirements.matches_factor(mock_factor))
        
        # Test non-matching group
        mock_factor.group = "volume"
        self.assertFalse(requirements.matches_factor(mock_factor))

    def test_source_priority_scoring(self):
        """Test source priority scoring."""
        requirements = DependencyRequirements(
            required_groups=["price"],
            preferred_sources=["ibkr", "fmp", "yahoo"],
            excluded_sources=["bad_source"]
        )
        
        # Test preferred source scoring
        self.assertEqual(requirements.get_source_priority_score("ibkr"), 100)
        self.assertEqual(requirements.get_source_priority_score("fmp"), 90)
        self.assertEqual(requirements.get_source_priority_score("yahoo"), 80)
        
        # Test excluded source
        self.assertEqual(requirements.get_source_priority_score("bad_source"), 0)
        
        # Test non-preferred source
        self.assertEqual(requirements.get_source_priority_score("unknown"), 20)

    def test_fallback_strategy_detection(self):
        """Test fallback strategy application logic."""
        requirements = DependencyRequirements(
            required_groups=["price"],
            min_sources=3,
            allow_single_source=False
        )
        
        # Test insufficient sources triggers fallback
        self.assertTrue(requirements.should_apply_fallback(2, {"ibkr", "fmp"}))
        
        # Test single source with min_sources > 1 triggers fallback
        self.assertTrue(requirements.should_apply_fallback(1, {"ibkr"}))
        
        # Test sufficient sources doesn't trigger fallback
        self.assertFalse(requirements.should_apply_fallback(3, {"ibkr", "fmp", "yahoo"}))


class TestDynamicDependencyResolver(unittest.TestCase):
    """Test cases for DynamicDependencyResolver service."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_factory = Mock()
        
        # Mock repositories
        self.mock_factory.factor_local_repo = Mock()
        self.mock_factory.factor_value_local_repo = Mock()
        self.mock_factory.financial_asset_local_repo = Mock()
        self.mock_factory.factor_value_ibkr_repo = Mock()
        
        self.resolver = DynamicDependencyResolver(self.mock_factory)
        
        self.test_entity = Mock()
        self.test_entity.id = 1
        self.test_entity.symbol = "AAPL"
        
        self.test_date = datetime(2025, 1, 15, 10, 0, 0)

    def test_discover_dependencies_basic(self):
        """Test basic dependency discovery."""
        requirements = DependencyRequirements(
            required_groups=["price"],
            min_sources=1
        )
        
        # Mock candidate factors
        mock_factor1 = Mock()
        mock_factor1.id = 1
        mock_factor1.group = "price"
        mock_factor1.subgroup = "close"
        mock_factor1.source = "ibkr"
        mock_factor1.name = "close"
        
        self.mock_factory.factor_local_repo.get_all.return_value = [mock_factor1]
        
        # Mock latest factor value (data available)
        mock_factor_value = Mock()
        mock_factor_value.date = self.test_date.date()
        mock_factor_value.value = "150.50"
        
        self.resolver._get_latest_factor_value_before_date = Mock(return_value=mock_factor_value)
        
        dependencies = self.resolver.discover_dependencies(
            requirements=requirements,
            entity=self.test_entity,
            target_date=self.test_date
        )
        
        self.assertEqual(len(dependencies), 1)
        self.assertEqual(dependencies[0]['factor'], mock_factor1)
        self.assertEqual(dependencies[0]['entity_id'], 1)

    def test_resolve_values_existing_data(self):
        """Test resolving dependency values from existing database data."""
        # Setup dependency info
        mock_factor = Mock()
        mock_factor.id = 1
        mock_factor.name = "close"
        
        dependencies = [{
            'factor': mock_factor,
            'parameter_name': 'close_price',
            'lag': timedelta(0),
            'entity_id': 1
        }]
        
        # Mock existing factor value in database
        mock_factor_value = Mock()
        mock_factor_value.value = "150.50"
        
        self.resolver._get_factor_value_from_db = Mock(return_value=mock_factor_value)
        
        resolved_values = self.resolver.resolve_values(
            dependencies=dependencies,
            target_date=self.test_date,
            entity_id=1
        )
        
        self.assertEqual(resolved_values['close_price'], 150.50)

    def test_resolve_values_create_missing(self):
        """Test creating missing dependency values."""
        # Setup dependency info
        mock_factor = Mock()
        mock_factor.id = 1
        mock_factor.name = "close"
        
        dependencies = [{
            'factor': mock_factor,
            'parameter_name': 'close_price',
            'lag': timedelta(0),
            'entity_id': 1
        }]
        
        # Mock no existing value, but successful creation
        self.resolver._get_factor_value_from_db = Mock(return_value=None)
        
        mock_created_value = Mock()
        mock_created_value.value = "150.50"
        self.resolver._create_missing_dependency = Mock(return_value=mock_created_value)
        
        resolved_values = self.resolver.resolve_values(
            dependencies=dependencies,
            target_date=self.test_date,
            entity_id=1
        )
        
        self.assertEqual(resolved_values['close_price'], 150.50)
        self.resolver._create_missing_dependency.assert_called_once()

    def test_filter_by_availability(self):
        """Test filtering factors by data availability."""
        # Mock factors
        mock_factor1 = Mock()
        mock_factor1.id = 1
        mock_factor1.name = "close"
        
        mock_factor2 = Mock()
        mock_factor2.id = 2
        mock_factor2.name = "volume"
        
        factors = [mock_factor1, mock_factor2]
        
        # Mock factor value for factor1 (available)
        mock_factor_value1 = Mock()
        mock_factor_value1.date = self.test_date.date()
        
        # Mock no factor value for factor2 (unavailable)
        def mock_get_latest(factor_id, entity_id, target_date):
            if factor_id == 1:
                return mock_factor_value1
            return None
        
        self.resolver._get_latest_factor_value_before_date = Mock(side_effect=mock_get_latest)
        
        available = self.resolver._filter_by_availability(
            factors=factors,
            entity=self.test_entity,
            target_date=self.test_date,
            max_age_days=1
        )
        
        self.assertEqual(len(available), 1)
        self.assertEqual(available[0]['factor'], mock_factor1)

    def test_prioritize_by_source(self):
        """Test source prioritization logic."""
        requirements = DependencyRequirements(
            required_groups=["price"],
            preferred_sources=["ibkr", "fmp"],
            max_sources=2
        )
        
        # Mock factors from different sources
        mock_factor_ibkr = Mock()
        mock_factor_ibkr.name = "close"
        mock_factor_ibkr.group = "price"
        mock_factor_ibkr.subgroup = "close"
        mock_factor_ibkr.source = "ibkr"
        
        mock_factor_yahoo = Mock()
        mock_factor_yahoo.name = "close"
        mock_factor_yahoo.group = "price"
        mock_factor_yahoo.subgroup = "close"
        mock_factor_yahoo.source = "yahoo"
        
        mock_factor_fmp = Mock()
        mock_factor_fmp.name = "close"
        mock_factor_fmp.group = "price"
        mock_factor_fmp.subgroup = "close"
        mock_factor_fmp.source = "fmp"
        
        available_factors = [
            {'factor': mock_factor_yahoo},
            {'factor': mock_factor_ibkr}, 
            {'factor': mock_factor_fmp}
        ]
        
        prioritized = self.resolver._prioritize_by_source(
            available_factors=available_factors,
            requirements=requirements
        )
        
        # Should be ordered by preference: ibkr (100), fmp (90), yahoo (20)
        self.assertEqual(prioritized[0]['factor'].source, "ibkr")
        self.assertEqual(prioritized[1]['factor'].source, "fmp")
        self.assertEqual(len(prioritized), 3)  # max_sources limits applied per group

    def test_fallback_use_close_for_mid(self):
        """Test fallback strategy using close price for mid price."""
        requirements = DependencyRequirements(
            required_groups=["price"],
            required_subgroups=["mid_price"],
            fallback_strategies=["use_close_if_no_mid"]
        )
        
        # Mock no mid_price factors available initially
        factors = []
        
        # Mock close price factor available as fallback
        mock_close_factor = Mock()
        mock_close_factor.subgroup = "close"
        mock_close_factor.group = "price"
        
        # Mock _find_candidate_factors to return close factor
        self.resolver._find_candidate_factors = Mock(return_value=[mock_close_factor])
        
        # Mock _filter_by_availability to return available close factor
        available_close = [{'factor': mock_close_factor}]
        self.resolver._filter_by_availability = Mock(return_value=available_close)
        
        result = self.resolver._fallback_use_close_for_mid(
            factors=factors,
            requirements=requirements,
            entity=self.test_entity,
            target_date=self.test_date
        )
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['factor'], mock_close_factor)


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with existing static dependency system."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_factory = Mock()
        self.mock_factor_value_repo = Mock()
        
        # Import the actual class for testing
        from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository
        
        self.ibkr_repo = IBKRFactorValueRepository(
            ibkr_client=Mock(),
            factory=self.mock_factory
        )

    def test_static_dependency_fallback(self):
        """Test that factors without get_dependency_requirements use static dependencies."""
        # Mock factor without dynamic dependency support
        mock_factor = Mock()
        mock_factor.id = 1
        mock_factor.name = "legacy_factor"
        # No get_dependency_requirements method
        
        self.mock_factory.factor_local_repo = Mock()
        self.mock_factory.factor_local_repo.get_by_id.return_value = mock_factor
        self.mock_factory.factor_dependency_local_repo = Mock()
        self.mock_factory.factor_dependency_local_repo.get_by_dependent_factor_id.return_value = []
        
        dependencies = self.ibkr_repo._get_factor_dependencies_from_db(1)
        
        # Should return empty list (no static dependencies) but not crash
        self.assertEqual(dependencies, [])

    def test_dynamic_dependency_detection(self):
        """Test that factors with get_dependency_requirements use dynamic resolution."""
        # Mock factor with dynamic dependency support
        mock_factor = Mock()
        mock_factor.id = 1
        mock_factor.name = "dynamic_factor"
        mock_factor.get_dependency_requirements = Mock()
        
        self.mock_factory.factor_local_repo = Mock()
        self.mock_factory.factor_local_repo.get_by_id.return_value = mock_factor
        
        dependencies = self.ibkr_repo._get_factor_dependencies_from_db(1)
        
        # Should return dynamic resolution marker
        self.assertEqual(len(dependencies), 1)
        self.assertTrue(dependencies[0]['dynamic_resolution_required'])
        self.assertEqual(dependencies[0]['factor'], mock_factor)


if __name__ == '__main__':
    unittest.main()