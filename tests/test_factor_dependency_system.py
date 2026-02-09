"""
Comprehensive tests for the factor dependency system.
Tests the discriminator-based dependency resolution, DAG validation, and integration.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
from typing import Dict, Any, Optional

# Import the new dependency system components
from src.domain.entities.factor.factor_dependency import (
    FactorDiscriminator,
    FactorReference,
    FactorDependency,
    FactorDependencyGraph,
    InMemoryFactorDependencyRegistry,
    FactorDependencyValidator,
    CyclicDependencyError
)
from src.domain.entities.factor.factor_dependency_resolver import (
    FactorDependencyResolver,
    DependencyResolutionContext,
    FactorDependencyResolutionError
)
from src.domain.entities.factor.factor import Factor


class MockFactor(Factor):
    """Mock factor for testing."""
    
    def __init__(self, name: str, factor_id: Optional[int] = None, dependencies: Optional[Dict[str, Any]] = None):
        super().__init__(
            name=name,
            group="Test",
            subgroup="Mock",
            data_type="float",
            source="test",
            definition=f"Mock factor {name}",
            factor_id=factor_id
        )
        if dependencies:
            self.__class__.dependencies = dependencies
    
    def calculate(self, **kwargs) -> Optional[float]:
        """Mock calculate method."""
        # Simple calculation based on provided parameters
        total = 0.0
        for key, value in kwargs.items():
            if isinstance(value, (int, float)):
                total += float(value)
        return total if total > 0 else None


class TestFactorDiscriminator(unittest.TestCase):
    """Test FactorDiscriminator functionality."""
    
    def test_discriminator_creation(self):
        """Test creating and using discriminators."""
        discriminator = FactorDiscriminator(code="TEST_FACTOR", version="v1")
        
        self.assertEqual(discriminator.code, "TEST_FACTOR")
        self.assertEqual(discriminator.version, "v1")
        self.assertEqual(discriminator.to_key(), "TEST_FACTOR:v1")
    
    def test_discriminator_from_key(self):
        """Test creating discriminator from key string."""
        key = "MARKET_PRICE:v2"
        discriminator = FactorDiscriminator.from_key(key)
        
        self.assertEqual(discriminator.code, "MARKET_PRICE")
        self.assertEqual(discriminator.version, "v2")
    
    def test_invalid_discriminator_key(self):
        """Test error handling for invalid key format."""
        with self.assertRaises(ValueError):
            FactorDiscriminator.from_key("invalid_key")
    
    def test_empty_discriminator_fields(self):
        """Test validation of required fields."""
        with self.assertRaises(ValueError):
            FactorDiscriminator(code="", version="v1")
        
        with self.assertRaises(ValueError):
            FactorDiscriminator(code="TEST", version="")


class TestFactorReference(unittest.TestCase):
    """Test FactorReference functionality."""
    
    def test_factor_reference_creation(self):
        """Test creating factor references with discriminators."""
        discriminator = FactorDiscriminator(code="SPOT_PRICE", version="v1")
        reference = FactorReference(
            discriminator=discriminator,
            name="Spot Price",
            group="Market Price",
            subgroup="Spot",
            source="IBKR"
        )
        
        self.assertEqual(reference.name, "Spot Price")
        self.assertEqual(reference.group, "Market Price")
        self.assertEqual(reference.discriminator.code, "SPOT_PRICE")
    
    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        discriminator = FactorDiscriminator(code="FUTURE_PRICE", version="v1")
        reference = FactorReference(
            discriminator=discriminator,
            name="Future Price",
            group="Market Price",
            source="IBKR"
        )
        
        # Test serialization
        data = reference.to_dict()
        self.assertIn("discriminator", data)
        self.assertEqual(data["discriminator"]["code"], "FUTURE_PRICE")
        self.assertEqual(data["name"], "Future Price")
        
        # Test deserialization
        restored_reference = FactorReference.from_dict(data)
        self.assertEqual(restored_reference.discriminator.code, "FUTURE_PRICE")
        self.assertEqual(restored_reference.name, "Future Price")


class TestFactorDependencyGraph(unittest.TestCase):
    """Test FactorDependencyGraph functionality."""
    
    def setUp(self):
        """Set up test dependencies in the format specified in the issue."""
        self.dependencies_dict = {
            "spot_price": {
                "factor": {
                    "discriminator": {
                        "code": "MARKET_SPOT_PRICE",
                        "version": "v1",
                    },
                    "name": "Spot Price",
                    "group": "Market Price",
                    "subgroup": "Spot",
                    "source": "IBKR",
                },
                "required": True,
            },
            "future_price": {
                "factor": {
                    "discriminator": {
                        "code": "MARKET_FUTURE_PRICE",
                        "version": "v1",
                    },
                    "name": "Future Price",
                    "group": "Market Price",
                    "subgroup": "Future",
                    "source": "IBKR",
                },
                "required": True,
            },
            "T": {
                "factor": {
                    "discriminator": {
                        "code": "FUTURE_TIME_TO_MATURITY",
                        "version": "v1",
                    },
                    "name": "Time To Maturity",
                    "group": "Future Factor",
                    "subgroup": "Contract",
                    "source": "model",
                },
                "required": True,
            },
        }
    
    def test_create_from_dependencies_dict(self):
        """Test creating dependency graph from issue format."""
        graph = FactorDependencyGraph.from_dependencies_dict(self.dependencies_dict)
        
        self.assertEqual(len(graph.dependencies), 3)
        self.assertIn("spot_price", graph.dependencies)
        self.assertIn("future_price", graph.dependencies)
        self.assertIn("T", graph.dependencies)
        
        # Check discriminators
        spot_dep = graph.get_dependency("spot_price")
        self.assertEqual(spot_dep.factor_reference.discriminator.code, "MARKET_SPOT_PRICE")
        self.assertTrue(spot_dep.required)
    
    def test_to_dependencies_dict(self):
        """Test converting back to dictionary format."""
        graph = FactorDependencyGraph.from_dependencies_dict(self.dependencies_dict)
        restored_dict = graph.to_dependencies_dict()
        
        # Check structure is preserved
        self.assertEqual(len(restored_dict), 3)
        self.assertIn("spot_price", restored_dict)
        
        spot_data = restored_dict["spot_price"]
        self.assertEqual(spot_data["factor"]["discriminator"]["code"], "MARKET_SPOT_PRICE")
        self.assertTrue(spot_data["required"])
    
    def test_required_and_optional_dependencies(self):
        """Test filtering required vs optional dependencies."""
        # Add optional dependency
        deps_with_optional = dict(self.dependencies_dict)
        deps_with_optional["optional_param"] = {
            "factor": {
                "discriminator": {"code": "OPTIONAL_FACTOR", "version": "v1"},
                "name": "Optional Factor"
            },
            "required": False
        }
        
        graph = FactorDependencyGraph.from_dependencies_dict(deps_with_optional)
        
        required_deps = graph.get_required_dependencies()
        optional_deps = graph.get_optional_dependencies()
        
        self.assertEqual(len(required_deps), 3)
        self.assertEqual(len(optional_deps), 1)
        self.assertEqual(optional_deps[0].parameter_name, "optional_param")


class TestInMemoryFactorDependencyRegistry(unittest.TestCase):
    """Test the in-memory factor registry."""
    
    def setUp(self):
        """Set up test registry and factors."""
        self.registry = InMemoryFactorDependencyRegistry()
        self.mock_factor = MockFactor("Test Factor", factor_id=1)
        self.discriminator = FactorDiscriminator(code="TEST_FACTOR", version="v1")
    
    def test_register_and_resolve_factor(self):
        """Test registering and resolving factors by discriminator."""
        # Register factor
        self.registry.register_factor(self.mock_factor, self.discriminator)
        
        # Resolve factor
        resolved_factor = self.registry.resolve_factor(self.discriminator)
        
        self.assertIsNotNone(resolved_factor)
        self.assertEqual(resolved_factor.name, "Test Factor")
        self.assertEqual(self.registry.get_factor_count(), 1)
    
    def test_resolve_nonexistent_factor(self):
        """Test resolving a factor that doesn't exist."""
        nonexistent_discriminator = FactorDiscriminator(code="NONEXISTENT", version="v1")
        resolved_factor = self.registry.resolve_factor(nonexistent_discriminator)
        
        self.assertIsNone(resolved_factor)
    
    def test_list_registered_factors(self):
        """Test listing all registered factors."""
        # Register multiple factors
        factor1 = MockFactor("Factor 1", factor_id=1)
        factor2 = MockFactor("Factor 2", factor_id=2)
        disc1 = FactorDiscriminator(code="FACTOR_1", version="v1")
        disc2 = FactorDiscriminator(code="FACTOR_2", version="v1")
        
        self.registry.register_factor(factor1, disc1)
        self.registry.register_factor(factor2, disc2)
        
        registered_discriminators = self.registry.list_registered_factors()
        
        self.assertEqual(len(registered_discriminators), 2)
        codes = [disc.code for disc in registered_discriminators]
        self.assertIn("FACTOR_1", codes)
        self.assertIn("FACTOR_2", codes)


class TestFactorDependencyValidator(unittest.TestCase):
    """Test DAG validation and cycle detection."""
    
    def setUp(self):
        """Set up test factors with dependencies."""
        self.registry = InMemoryFactorDependencyRegistry()
        self.validator = FactorDependencyValidator(self.registry)
        
        # Create factors with potential cycles
        self.factor_a = MockFactor("Factor A", factor_id=1)
        self.factor_b = MockFactor("Factor B", factor_id=2)
        self.factor_c = MockFactor("Factor C", factor_id=3)
        
        # Register factors
        disc_a = FactorDiscriminator(code="FACTOR_A", version="v1")
        disc_b = FactorDiscriminator(code="FACTOR_B", version="v1") 
        disc_c = FactorDiscriminator(code="FACTOR_C", version="v1")
        
        self.registry.register_factor(self.factor_a, disc_a)
        self.registry.register_factor(self.factor_b, disc_b)
        self.registry.register_factor(self.factor_c, disc_c)
    
    def test_detect_cycle(self):
        """Test cycle detection in dependency graph."""
        # Create a cycle: A depends on B, B depends on C, C depends on A
        self.factor_a.__class__.dependencies = {
            "param_b": {
                "factor": {
                    "discriminator": {"code": "FACTOR_B", "version": "v1"}
                },
                "required": True
            }
        }
        
        self.factor_b.__class__.dependencies = {
            "param_c": {
                "factor": {
                    "discriminator": {"code": "FACTOR_C", "version": "v1"}
                },
                "required": True
            }
        }
        
        self.factor_c.__class__.dependencies = {
            "param_a": {
                "factor": {
                    "discriminator": {"code": "FACTOR_A", "version": "v1"}
                },
                "required": True
            }
        }
        
        # Should detect cycle
        with self.assertRaises(CyclicDependencyError):
            self.validator.validate_dag([self.factor_a])
    
    def test_valid_dag(self):
        """Test validation of valid DAG without cycles."""
        # Create valid dependencies: A depends on B, B depends on C, no cycles
        self.factor_a.__class__.dependencies = {
            "param_b": {
                "factor": {
                    "discriminator": {"code": "FACTOR_B", "version": "v1"}
                },
                "required": True
            }
        }
        
        self.factor_b.__class__.dependencies = {
            "param_c": {
                "factor": {
                    "discriminator": {"code": "FACTOR_C", "version": "v1"}
                },
                "required": True
            }
        }
        
        # Factor C has no dependencies - terminal node
        self.factor_c.__class__.dependencies = {}
        
        # Should not raise exception for valid DAG
        try:
            self.validator.validate_dag([self.factor_a])
        except CyclicDependencyError:
            self.fail("Valid DAG incorrectly flagged as cyclic")


class TestFactorDependencyResolver(unittest.TestCase):
    """Test the main dependency resolver."""
    
    def setUp(self):
        """Set up resolver with mock data source."""
        self.registry = InMemoryFactorDependencyRegistry()
        self.mock_data_source = Mock()
        self.resolver = FactorDependencyResolver(
            registry=self.registry,
            data_source_resolver=self.mock_data_source
        )
        
        # Create test factor with dependencies
        dependencies = {
            "spot_price": {
                "factor": {
                    "discriminator": {"code": "SPOT_PRICE", "version": "v1"},
                    "name": "Spot Price"
                },
                "required": True
            },
            "interest_rate": {
                "factor": {
                    "discriminator": {"code": "INTEREST_RATE", "version": "v1"},
                    "name": "Interest Rate"
                },
                "required": True
            }
        }
        
        self.test_factor = MockFactor("Test Factor", factor_id=1, dependencies=dependencies)
        
        # Register dependency factors
        self.spot_factor = MockFactor("Spot Price", factor_id=2)
        self.rate_factor = MockFactor("Interest Rate", factor_id=3)
        
        spot_disc = FactorDiscriminator(code="SPOT_PRICE", version="v1")
        rate_disc = FactorDiscriminator(code="INTEREST_RATE", version="v1")
        
        self.registry.register_factor(self.spot_factor, spot_disc)
        self.registry.register_factor(self.rate_factor, rate_disc)
    
    def test_resolve_dependencies(self):
        """Test resolving all dependencies for a factor."""
        # Mock data source to return values for registered factors
        self.mock_data_source.resolve_by_discriminator.side_effect = [100.0, 0.05]  # spot price, interest rate
        
        context = DependencyResolutionContext(
            timestamp=datetime.now(),
            entity_id=1
        )
        
        resolved_deps = self.resolver.resolve_dependencies(self.test_factor, context)
        
        self.assertEqual(len(resolved_deps), 2)
        self.assertIn("spot_price", resolved_deps)
        self.assertIn("interest_rate", resolved_deps)
    
    def test_calculate_factor_with_dependencies(self):
        """Test end-to-end factor calculation with dependencies."""
        # Mock the calculate method to return sum of dependencies
        self.test_factor.calculate = Mock(return_value=105.05)
        
        # Mock data source
        self.mock_data_source.resolve_by_discriminator.side_effect = [100.0, 0.05]
        
        context = DependencyResolutionContext(
            timestamp=datetime.now(),
            entity_id=1
        )
        
        result = self.resolver.calculate_factor_with_dependencies(self.test_factor, context)
        
        self.assertEqual(result, 105.05)
        self.test_factor.calculate.assert_called_once()
    
    def test_missing_required_dependency(self):
        """Test error handling for missing required dependencies."""
        # Mock data source to fail for one dependency
        self.mock_data_source.resolve_by_discriminator.side_effect = [100.0, None]  # second dependency fails
        
        context = DependencyResolutionContext(
            timestamp=datetime.now(),
            entity_id=1
        )
        
        with self.assertRaises(FactorDependencyResolutionError):
            self.resolver.resolve_dependencies(self.test_factor, context)
    
    def test_recursive_dependency_resolution(self):
        """Test recursive resolution of nested dependencies."""
        # Create a factor that depends on the test_factor
        recursive_dependencies = {
            "calculated_factor": {
                "factor": {
                    "discriminator": {"code": "TEST_FACTOR", "version": "v1"},
                    "name": "Test Factor"
                },
                "required": True
            }
        }
        
        recursive_factor = MockFactor("Recursive Factor", factor_id=4, dependencies=recursive_dependencies)
        test_disc = FactorDiscriminator(code="TEST_FACTOR", version="v1")
        self.registry.register_factor(self.test_factor, test_disc)
        
        # Mock data sources
        self.mock_data_source.resolve_by_discriminator.side_effect = [100.0, 0.05]  # for nested dependencies
        
        context = DependencyResolutionContext(
            timestamp=datetime.now(),
            entity_id=1
        )
        
        # Should recursively resolve the dependencies
        resolved_deps = self.resolver.resolve_dependencies(recursive_factor, context)
        
        self.assertIn("calculated_factor", resolved_deps)


class TestIntegrationWithIBKRRepository(unittest.TestCase):
    """Test integration with the enhanced IBKR repository."""
    
    @patch('src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository.InMemoryFactorDependencyRegistry')
    @patch('src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository.FactorDependencyResolver')
    def test_repository_initialization(self, mock_resolver_class, mock_registry_class):
        """Test that repository properly initializes dependency system."""
        from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository
        
        mock_ibkr_client = Mock()
        mock_factory = Mock()
        mock_factory.instrument_factor_ibkr_repo = Mock()
        
        # Create repository
        repo = IBKRFactorValueRepository(mock_ibkr_client, factory=mock_factory)
        
        # Verify dependency system components were initialized
        mock_registry_class.assert_called_once()
        mock_resolver_class.assert_called_once()
    
    def test_discriminator_format_detection(self):
        """Test detection of discriminator-based dependency format."""
        from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository
        
        mock_ibkr_client = Mock()
        mock_factory = Mock()
        mock_factory.instrument_factor_ibkr_repo = Mock()
        
        repo = IBKRFactorValueRepository(mock_ibkr_client, factory=mock_factory)
        
        # Create factor with new discriminator format
        dependencies = {
            "spot_price": {
                "factor": {
                    "discriminator": {"code": "SPOT_PRICE", "version": "v1"}
                },
                "required": True
            }
        }
        
        factor = MockFactor("Test Factor", dependencies=dependencies)
        extracted_deps = repo._get_factor_dependencies(factor)
        
        # Should return the discriminator format dependencies
        self.assertEqual(len(extracted_deps), 1)
        self.assertIn("spot_price", extracted_deps)
        self.assertIn("discriminator", extracted_deps["spot_price"]["factor"])


if __name__ == '__main__':
    unittest.main()