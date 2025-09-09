"""
Comprehensive unit tests for the Optimizer module.
Tests parameter management, optimization algorithms, and result handling.
"""

import unittest
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch

# Import optimizer modules
from src.application.services.misbuffet.optimizer import (
    OptimizationType, SelectionType, CrossoverType, MutationType,
    OptimizationParameter, OptimizationParameterSet, ParameterSpace,
    OptimizationResult, PerformanceMetrics, OptimizationStatistics,
    OptimizerConfiguration, OptimizationNodePacket,
    GeneticOptimizer, GridSearchOptimizer, RandomOptimizer,
    OptimizerFactory, Individual, Population,
    ParameterType, FitnessMetric, ObjectiveDirection
)
from src.application.services.misbuffet.optimizer.interfaces import IOptimizationTarget


class MockOptimizationTarget(IOptimizationTarget):
    """Mock optimization target for testing."""
    
    def __init__(self, fitness_function=None):
        self.fitness_function = fitness_function or self._default_fitness
        self.evaluation_count = 0
    
    async def evaluate(self, parameter_set: OptimizationParameterSet) -> OptimizationResult:
        """Mock evaluation that returns a simple fitness based on parameters."""
        self.evaluation_count += 1
        
        # Calculate fitness based on parameters
        fitness = self.fitness_function(parameter_set.parameters)
        
        # Create mock performance metrics
        metrics = PerformanceMetrics(
            total_return=fitness * 0.1,
            sharpe_ratio=fitness,
            maximum_drawdown=-abs(fitness) * 0.05,
            volatility=abs(fitness) * 0.2,
            win_rate=min(1.0, abs(fitness) * 0.1),
            total_trades=100
        )
        
        return OptimizationResult(
            parameter_set=parameter_set,
            performance_metrics=metrics,
            backtest_id=f"test_{self.evaluation_count}",
            execution_time=0.1,
            fitness=fitness
        )
    
    def get_objectives(self) -> List[str]:
        return ["sharpe_ratio"]
    
    def validate_parameters(self, parameter_set: OptimizationParameterSet) -> bool:
        return True
    
    def _default_fitness(self, parameters: Dict[str, Any]) -> float:
        """Default fitness function: negative sum of squares (to test minimization)."""
        total = 0.0
        for value in parameters.values():
            if isinstance(value, (int, float)):
                total += value ** 2
        return -total  # Negative for minimization problem


class TestParameterManagement(unittest.TestCase):
    """Test parameter management components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.param_space = ParameterSpace("test_space")
    
    def test_optimization_parameter_creation(self):
        """Test OptimizationParameter creation and validation."""
        # Test float parameter
        param = OptimizationParameter(
            name="test_param",
            min_value=0.0,
            max_value=1.0,
            parameter_type=ParameterType.FLOAT
        )
        
        self.assertEqual(param.name, "test_param")
        self.assertEqual(param.min_value, 0.0)
        self.assertEqual(param.max_value, 1.0)
        self.assertTrue(param.validate_value(0.5))
        self.assertFalse(param.validate_value(1.5))
        
        # Test random value generation
        for _ in range(10):
            value = param.generate_random_value()
            self.assertTrue(param.validate_value(value))
    
    def test_optimization_parameter_types(self):
        """Test different parameter types."""
        # Integer parameter
        int_param = OptimizationParameter(
            name="int_param",
            min_value=1,
            max_value=10,
            parameter_type=ParameterType.INTEGER
        )
        
        value = int_param.generate_random_value()
        self.assertIsInstance(value, (int, np.integer))
        self.assertTrue(1 <= value <= 10)
        
        # Boolean parameter
        bool_param = OptimizationParameter(
            name="bool_param",
            min_value=False,
            max_value=True,
            parameter_type=ParameterType.BOOLEAN
        )
        
        value = bool_param.generate_random_value()
        self.assertIsInstance(value, bool)
        
        # Categorical parameter
        cat_param = OptimizationParameter(
            name="cat_param",
            min_value="",
            max_value="",
            parameter_type=ParameterType.CATEGORICAL,
            allowed_values=["A", "B", "C"]
        )
        
        value = cat_param.generate_random_value()
        self.assertIn(value, ["A", "B", "C"])
    
    def test_parameter_space(self):
        """Test ParameterSpace functionality."""
        # Add parameters
        param1 = OptimizationParameter("param1", 0.0, 1.0, ParameterType.FLOAT, step=0.1)
        param2 = OptimizationParameter("param2", 1, 5, ParameterType.INTEGER)
        
        self.param_space.add_parameter(param1)
        self.param_space.add_parameter(param2)
        
        self.assertEqual(len(self.param_space), 2)
        self.assertIn("param1", self.param_space)
        self.assertIn("param2", self.param_space)
        
        # Test random parameter set generation
        param_set = self.param_space.generate_random_parameter_set()
        self.assertEqual(len(param_set.parameters), 2)
        self.assertTrue(self.param_space.validate_parameter_set(param_set))
        
        # Test total combinations
        total_combinations = self.param_space.get_total_combinations()
        self.assertIsInstance(total_combinations, int)
        self.assertGreater(total_combinations, 0)
    
    def test_parameter_set_operations(self):
        """Test OptimizationParameterSet operations."""
        parameters = {"param1": 0.5, "param2": 3}
        param_set = OptimizationParameterSet(parameters=parameters)
        
        self.assertEqual(param_set.get_parameter_value("param1"), 0.5)
        self.assertEqual(param_set.get_parameter_value("param2"), 3)
        self.assertIsNone(param_set.get_parameter_value("nonexistent"))
        
        # Test copy
        copied_set = param_set.copy()
        self.assertNotEqual(param_set.unique_id, copied_set.unique_id)
        self.assertEqual(param_set.parameters, copied_set.parameters)
        
        # Test serialization
        param_dict = param_set.to_dict()
        restored_set = OptimizationParameterSet.from_dict(param_dict)
        self.assertEqual(param_set.parameters, restored_set.parameters)


class TestResultManagement(unittest.TestCase):
    """Test result management components."""
    
    def test_performance_metrics(self):
        """Test PerformanceMetrics functionality."""
        metrics = PerformanceMetrics(
            total_return=0.15,
            sharpe_ratio=1.5,
            maximum_drawdown=-0.08,
            volatility=0.12,
            win_rate=0.65,
            total_trades=150
        )
        
        # Test fitness calculation
        fitness = metrics.calculate_fitness(FitnessMetric.SHARPE_RATIO)
        self.assertEqual(fitness, 1.5)
        
        fitness_min = metrics.calculate_fitness(FitnessMetric.MAXIMUM_DRAWDOWN, ObjectiveDirection.MINIMIZE)
        self.assertEqual(fitness_min, 0.08)  # Negative of -0.08
        
        # Test validation
        self.assertTrue(metrics.is_valid())
        
        # Test with invalid values
        metrics.sharpe_ratio = float('nan')
        self.assertFalse(metrics.is_valid())
        
        # Test normalization
        metrics.normalize_metrics()
        self.assertEqual(metrics.sharpe_ratio, 0.0)  # NaN should be replaced with 0.0
    
    def test_optimization_result(self):
        """Test OptimizationResult functionality."""
        param_set = OptimizationParameterSet(parameters={"param1": 0.5})
        metrics = PerformanceMetrics(sharpe_ratio=1.2)
        
        result = OptimizationResult(
            parameter_set=param_set,
            performance_metrics=metrics,
            backtest_id="test_001",
            execution_time=2.5
        )
        
        self.assertTrue(result.is_successful())
        self.assertEqual(result.fitness, 1.2)
        
        # Test serialization
        result_dict = result.to_dict()
        restored_result = OptimizationResult.from_dict(result_dict)
        self.assertEqual(result.backtest_id, restored_result.backtest_id)
    
    def test_optimization_statistics(self):
        """Test OptimizationStatistics functionality."""
        stats = OptimizationStatistics(
            optimization_id="test_opt",
            start_time=datetime.now()
        )
        
        # Create mock results
        results = []
        for i in range(10):
            param_set = OptimizationParameterSet(parameters={"param": i})
            metrics = PerformanceMetrics(sharpe_ratio=i * 0.1)
            result = OptimizationResult(
                parameter_set=param_set,
                performance_metrics=metrics,
                backtest_id=f"test_{i}",
                execution_time=1.0,
                fitness=i * 0.1
            )
            results.append(result)
        
        stats.update_with_results(results)
        
        self.assertEqual(stats.total_runs_completed, 10)
        self.assertIsNotNone(stats.best_result)
        self.assertIsNotNone(stats.worst_result)
        self.assertGreater(stats.mean_fitness, 0)


class TestOptimizers(unittest.TestCase):
    """Test optimization algorithms."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create parameter space
        self.param_space = ParameterSpace("test_space")
        self.param_space.add_parameter(OptimizationParameter("x", -5.0, 5.0, ParameterType.FLOAT))
        self.param_space.add_parameter(OptimizationParameter("y", -5.0, 5.0, ParameterType.FLOAT))
        
        # Create target function (minimize x^2 + y^2)
        self.target = MockOptimizationTarget()
        
        # Create configuration
        self.config = OptimizerConfiguration(
            max_concurrent_backtests=2,
            max_iterations=10
        )
    
    def test_genetic_optimizer_initialization(self):
        """Test GeneticOptimizer initialization."""
        optimizer = GeneticOptimizer(
            parameter_space=self.param_space,
            target_function=self.target,
            configuration=self.config
        )
        
        self.assertIsNotNone(optimizer.population)
        self.assertEqual(len(optimizer.population.individuals), self.config.population_size)
        self.assertFalse(optimizer.is_running)
        self.assertFalse(optimizer.is_stopped)
    
    def test_genetic_optimizer_optimization(self):
        """Test GeneticOptimizer optimization process."""
        config = OptimizerConfiguration(
            optimization_type=OptimizationType.GENETIC,
            population_size=10,
            max_generations=5,
            max_concurrent_backtests=2
        )
        
        optimizer = GeneticOptimizer(
            parameter_space=self.param_space,
            target_function=self.target,
            configuration=config
        )
        
        # Run optimization
        async def run_optimization():
            stats = await optimizer.optimize()
            return stats
        
        stats = asyncio.run(run_optimization())
        
        self.assertIsNotNone(stats)
        self.assertGreater(stats.total_runs_completed, 0)
        self.assertIsNotNone(optimizer.best_result)
        self.assertTrue(optimizer.is_complete())
    
    def test_grid_search_optimizer(self):
        """Test GridSearchOptimizer functionality."""
        # Create discrete parameter space
        param_space = ParameterSpace("grid_test")
        param_space.add_parameter(OptimizationParameter("x", 0, 2, ParameterType.INTEGER))
        param_space.add_parameter(OptimizationParameter("y", 0, 2, ParameterType.INTEGER))
        
        config = OptimizerConfiguration(
            optimization_type=OptimizationType.GRID_SEARCH,
            max_concurrent_backtests=2
        )
        
        optimizer = GridSearchOptimizer(
            parameter_space=param_space,
            target_function=self.target,
            configuration=config
        )
        
        # Test initialization
        optimizer.initialize(config)
        self.assertEqual(optimizer.total_combinations, 9)  # 3x3 grid
        
        # Run optimization
        async def run_optimization():
            return await optimizer.optimize()
        
        stats = asyncio.run(run_optimization())
        
        self.assertEqual(stats.total_runs_completed, 9)
        self.assertIsNotNone(optimizer.best_result)
    
    def test_random_optimizer(self):
        """Test RandomOptimizer functionality."""
        config = OptimizerConfiguration(
            optimization_type=OptimizationType.RANDOM,
            random_search_samples=20,
            max_concurrent_backtests=2
        )
        
        optimizer = RandomOptimizer(
            parameter_space=self.param_space,
            target_function=self.target,
            configuration=config
        )
        
        # Run optimization
        async def run_optimization():
            return await optimizer.optimize()
        
        stats = asyncio.run(run_optimization())
        
        self.assertEqual(stats.total_runs_completed, 20)
        self.assertIsNotNone(optimizer.best_result)
        self.assertGreater(optimizer.progress.get_efficiency(), 0.5)  # Should have good uniqueness


class TestGeneticAlgorithmComponents(unittest.TestCase):
    """Test genetic algorithm specific components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.param_space = ParameterSpace("ga_test")
        self.param_space.add_parameter(OptimizationParameter("x", 0.0, 10.0, ParameterType.FLOAT))
        self.param_space.add_parameter(OptimizationParameter("y", 0.0, 10.0, ParameterType.FLOAT))
    
    def test_individual_creation(self):
        """Test Individual creation and operations."""
        param_set = OptimizationParameterSet(parameters={"x": 5.0, "y": 3.0})
        individual = Individual(parameter_set=param_set, fitness=1.5, generation=1)
        
        self.assertEqual(individual.fitness, 1.5)
        self.assertEqual(individual.generation, 1)
        self.assertTrue(individual.is_evaluated())
        
        # Test copy
        copy_individual = individual.copy()
        self.assertNotEqual(individual.parameter_set.unique_id, copy_individual.parameter_set.unique_id)
        self.assertEqual(individual.fitness, copy_individual.fitness)
        
        # Test mutation
        individual.mutate_parameter("x", 7.0)
        self.assertEqual(individual.parameter_set.get_parameter_value("x"), 7.0)
        self.assertIsNone(individual.fitness)  # Should reset fitness after mutation
    
    def test_population_operations(self):
        """Test Population operations."""
        population = Population(size=10, parameter_space=self.param_space)
        population.initialize_random()
        
        self.assertEqual(len(population), 10)
        self.assertEqual(population.generation, 0)
        
        # Set fitness for some individuals
        for i, individual in enumerate(population.individuals[:5]):
            individual.fitness = i * 0.1
        
        population.update_statistics()
        
        # Test best/worst selection
        best_individuals = population.get_best_individuals(3)
        self.assertEqual(len(best_individuals), 3)
        self.assertGreaterEqual(best_individuals[0].fitness, best_individuals[1].fitness)
        
        worst_individuals = population.get_worst_individuals(2)
        self.assertEqual(len(worst_individuals), 2)
        self.assertLessEqual(worst_individuals[0].fitness, worst_individuals[1].fitness)
        
        # Test diversity calculation
        diversity = population.get_diversity()
        self.assertGreaterEqual(diversity, 0.0)


class TestOptimizerFactory(unittest.TestCase):
    """Test OptimizerFactory functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.factory = OptimizerFactory()
        self.param_space = ParameterSpace("factory_test")
        self.param_space.add_parameter(OptimizationParameter("x", 0.0, 1.0, ParameterType.FLOAT))
        self.target = MockOptimizationTarget()
    
    def test_supported_types(self):
        """Test supported optimizer types."""
        supported_types = self.factory.get_supported_types()
        
        self.assertIn(OptimizationType.GENETIC, supported_types)
        self.assertIn(OptimizationType.GRID_SEARCH, supported_types)
        self.assertIn(OptimizationType.RANDOM, supported_types)
    
    def test_create_genetic_optimizer(self):
        """Test creating genetic optimizer through factory."""
        optimizer = self.factory.create_optimizer(
            optimization_type=OptimizationType.GENETIC,
            parameter_space=self.param_space,
            target_function=self.target
        )
        
        self.assertIsInstance(optimizer, GeneticOptimizer)
        self.assertEqual(optimizer.parameter_space, self.param_space)
        self.assertEqual(optimizer.target_function, self.target)
    
    def test_create_grid_search_optimizer(self):
        """Test creating grid search optimizer through factory."""
        # Create discrete parameter space
        discrete_space = ParameterSpace("discrete")
        discrete_space.add_parameter(OptimizationParameter("x", 0, 2, ParameterType.INTEGER))
        
        optimizer = self.factory.create_optimizer(
            optimization_type=OptimizationType.GRID_SEARCH,
            parameter_space=discrete_space,
            target_function=self.target
        )
        
        self.assertIsInstance(optimizer, GridSearchOptimizer)
    
    def test_create_random_optimizer(self):
        """Test creating random optimizer through factory."""
        optimizer = self.factory.create_optimizer(
            optimization_type=OptimizationType.RANDOM,
            parameter_space=self.param_space,
            target_function=self.target
        )
        
        self.assertIsInstance(optimizer, RandomOptimizer)
    
    def test_recommended_configuration(self):
        """Test recommended configuration generation."""
        config = self.factory.get_recommended_configuration(
            optimization_type=OptimizationType.GENETIC,
            parameter_space=self.param_space,
            evaluation_budget=100
        )
        
        self.assertIsInstance(config, OptimizerConfiguration)
        self.assertEqual(config.optimization_type, OptimizationType.GENETIC)
        self.assertGreater(config.population_size, 0)
        self.assertGreater(config.max_generations, 0)
    
    def test_validation(self):
        """Test factory validation."""
        # Test invalid optimization type
        with self.assertRaises(TypeError):
            self.factory.create_optimizer(
                optimization_type="invalid",  # Should be enum
                parameter_space=self.param_space,
                target_function=self.target
            )
        
        # Test empty parameter space
        empty_space = ParameterSpace("empty")
        with self.assertRaises(ValueError):
            self.factory.create_optimizer(
                optimization_type=OptimizationType.GENETIC,
                parameter_space=empty_space,
                target_function=self.target
            )


class TestConfiguration(unittest.TestCase):
    """Test configuration management."""
    
    def test_optimizer_configuration(self):
        """Test OptimizerConfiguration functionality."""
        config = OptimizerConfiguration(
            optimization_type=OptimizationType.GENETIC,
            population_size=30,
            max_generations=50,
            mutation_rate=0.1
        )
        
        # Test validation
        errors = config.validate()
        self.assertEqual(len(errors), 0)
        self.assertTrue(config.is_valid())
        
        # Test invalid configuration
        config.population_size = -1
        errors = config.validate()
        self.assertGreater(len(errors), 0)
        self.assertFalse(config.is_valid())
        
        # Test serialization
        config_dict = config.to_dict()
        restored_config = OptimizerConfiguration.from_dict(config_dict)
        self.assertEqual(config.optimization_type, restored_config.optimization_type)
        self.assertEqual(config.mutation_rate, restored_config.mutation_rate)
    
    def test_optimization_node_packet(self):
        """Test OptimizationNodePacket functionality."""
        packet = OptimizationNodePacket(
            optimization_id="test_opt",
            algorithm_id="test_algo",
            parameter_set_id="test_params",
            algorithm_code="print('test')",
            initial_cash=100000.0
        )
        
        # Test validation
        errors = packet.validate()
        self.assertEqual(len(errors), 0)
        self.assertTrue(packet.is_valid())
        
        # Test status operations
        packet.mark_started()
        self.assertEqual(packet.status, "running")
        self.assertIsNotNone(packet.started_time)
        
        packet.mark_completed()
        self.assertEqual(packet.status, "completed")
        self.assertTrue(packet.is_successful())
        
        # Test serialization
        packet_dict = packet.to_dict()
        restored_packet = OptimizationNodePacket.from_dict(packet_dict)
        self.assertEqual(packet.optimization_id, restored_packet.optimization_id)


class TestIntegration(unittest.TestCase):
    """Integration tests for optimizer components."""
    
    def test_full_optimization_workflow(self):
        """Test complete optimization workflow."""
        # Create parameter space
        param_space = ParameterSpace("integration_test")
        param_space.add_parameter(OptimizationParameter("x", -2.0, 2.0, ParameterType.FLOAT))
        param_space.add_parameter(OptimizationParameter("y", -2.0, 2.0, ParameterType.FLOAT))
        
        # Create target function (minimize x^2 + y^2, optimum at x=0, y=0)
        target = MockOptimizationTarget()
        
        # Create configuration
        config = OptimizerConfiguration(
            optimization_type=OptimizationType.GENETIC,
            population_size=20,
            max_generations=10,
            max_concurrent_backtests=4,
            target_fitness=-0.1  # Close to zero (minimum)
        )
        
        # Create optimizer using factory
        factory = OptimizerFactory()
        optimizer = factory.create_optimizer(
            optimization_type=OptimizationType.GENETIC,
            parameter_space=param_space,
            target_function=target,
            configuration=config
        )
        
        # Run optimization
        async def run_test():
            stats = await optimizer.optimize()
            return stats
        
        stats = asyncio.run(run_test())
        
        # Verify results
        self.assertIsNotNone(stats)
        self.assertGreater(stats.total_runs_completed, 0)
        self.assertIsNotNone(optimizer.best_result)
        
        # Best result should be close to optimum (x=0, y=0)
        best_params = optimizer.best_result.parameter_set.parameters
        x_best = best_params.get("x", 0)
        y_best = best_params.get("y", 0)
        
        # Should find solution reasonably close to optimum
        distance_from_optimum = (x_best ** 2 + y_best ** 2) ** 0.5
        self.assertLess(distance_from_optimum, 2.0)  # Within reasonable bounds


if __name__ == '__main__':
    unittest.main()