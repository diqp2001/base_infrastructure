"""
Tests for the Optimizer.Launcher module.

Provides comprehensive testing for all optimizer launcher components including
configuration, worker management, result coordination, and main orchestrator.
"""

import unittest
import asyncio
import tempfile
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from pathlib import Path

from .interfaces import (
    OptimizerLauncherConfiguration,
    OptimizerLauncherMode,
    OptimizerLauncherStatus,
    WorkerStatus
)
from .configuration import (
    OptimizerLauncherConfigurationBuilder,
    OptimizerLauncherConfigurationManager,
    OptimizerParameterConfig,
    OptimizerTargetConfig,
    WorkerConfig
)
from .node_packet import (
    OptimizerNodePacket,
    NodePacketFactory,
    AlgorithmConfiguration,
    JobMetadata,
    ResourceRequirements
)
from .worker_manager import LocalWorkerManager, WorkerInfo
from .result_coordinator import ResultCoordinator, ProgressReporter
from .optimizer_launcher import OptimizerLauncher, OptimizerLauncherFactory

from ..optimizer.parameter_management import OptimizationParameterSet, OptimizationParameter
from ..optimizer.result_management import OptimizationResult, PerformanceMetrics
from ..optimizer.enums import ParameterType
from ..common.enums import Resolution, SecurityType


class TestOptimizerLauncherConfiguration(unittest.TestCase):
    """Test optimizer launcher configuration management."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = OptimizerLauncherConfigurationManager()
    
    def test_configuration_builder(self):
        """Test configuration builder pattern."""
        config = (OptimizerLauncherConfigurationBuilder()
                 .with_algorithm("TestAlgorithm", "test_algorithm.py")
                 .with_parameters("test_params.json")
                 .with_mode(OptimizerLauncherMode.LOCAL)
                 .with_concurrent_backtests(8)
                 .with_data_folder("test_data")
                 .with_output_folder("test_output")
                 .with_target(OptimizerTargetConfig(
                     name="sharpe_ratio",
                     objectives=["sharpe_ratio"],
                     maximize=True
                 ))
                 .with_worker_config(WorkerConfig(
                     worker_type="local",
                     max_workers=8,
                     timeout=1800
                 ))
                 .with_checkpointing(True, 25)
                 .with_fault_tolerance(True)
                 .build())
        
        self.assertEqual(config.algorithm_type_name, "TestAlgorithm")
        self.assertEqual(config.algorithm_location, "test_algorithm.py")
        self.assertEqual(config.parameter_file, "test_params.json")
        self.assertEqual(config.mode, OptimizerLauncherMode.LOCAL)
        self.assertEqual(config.max_concurrent_backtests, 8)
        self.assertEqual(config.data_folder, "test_data")
        self.assertEqual(config.output_folder, "test_output")
        self.assertTrue(config.enable_checkpointing)
        self.assertEqual(config.checkpoint_frequency, 25)
        self.assertTrue(config.fault_tolerance)
        
        # Check custom config
        self.assertIn('target_config', config.custom_config)
        self.assertIn('worker_config', config.custom_config)
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        # Valid configuration
        config = OptimizerLauncherConfiguration(
            optimization_target="sharpe_ratio",
            algorithm_type_name="TestAlgorithm",
            algorithm_location="test_algorithm.py",
            parameter_file="test_params.json"
        )
        
        # Create test files
        Path(self.temp_dir, "test_algorithm.py").touch()
        Path(self.temp_dir, "test_params.json").touch()
        Path(self.temp_dir, "data").mkdir(exist_ok=True)
        
        config.algorithm_location = str(Path(self.temp_dir, "test_algorithm.py"))
        config.parameter_file = str(Path(self.temp_dir, "test_params.json"))
        config.data_folder = str(Path(self.temp_dir, "data"))
        
        errors = self.config_manager.validate_configuration(config)
        self.assertEqual(len(errors), 0)
        
        # Invalid configuration
        invalid_config = OptimizerLauncherConfiguration(
            optimization_target="",
            algorithm_type_name="",
            algorithm_location="nonexistent.py",
            parameter_file="nonexistent.json",
            max_concurrent_backtests=-1
        )
        
        errors = self.config_manager.validate_configuration(invalid_config)
        self.assertGreater(len(errors), 0)
    
    def test_configuration_save_load(self):
        """Test saving and loading configuration."""
        config = OptimizerLauncherConfiguration(
            optimization_target="sharpe_ratio",
            algorithm_type_name="TestAlgorithm",
            algorithm_location="test_algorithm.py",
            parameter_file="test_params.json",
            mode=OptimizerLauncherMode.LOCAL
        )
        
        config_file = Path(self.temp_dir, "test_config.json")
        
        # Save configuration
        success = self.config_manager.save_configuration(config, str(config_file))
        self.assertTrue(success)
        self.assertTrue(config_file.exists())
        
        # Load configuration
        loaded_config = self.config_manager.load_from_file(str(config_file))
        self.assertEqual(loaded_config.optimization_target, config.optimization_target)
        self.assertEqual(loaded_config.algorithm_type_name, config.algorithm_type_name)
        self.assertEqual(loaded_config.mode, config.mode)


class TestOptimizerNodePacket(unittest.TestCase):
    """Test optimizer node packet functionality."""
    
    def setUp(self):
        self.parameter_set = OptimizationParameterSet()
        self.parameter_set.add_parameter("param1", 10.0)
        self.parameter_set.add_parameter("param2", "value1")
        
        self.algorithm_config = AlgorithmConfiguration(
            algorithm_type_name="TestAlgorithm",
            algorithm_location="test_algorithm.py",
            start_date="2020-01-01",
            end_date="2021-01-01",
            initial_cash=100000.0,
            resolution=Resolution.DAILY
        )
    
    def test_node_packet_creation(self):
        """Test node packet creation."""
        packet = OptimizerNodePacket(
            parameter_set=self.parameter_set,
            algorithm_config=self.algorithm_config
        )
        
        self.assertIsNotNone(packet.job_id)
        self.assertEqual(packet.parameter_set, self.parameter_set)
        self.assertIsInstance(packet.algorithm_config, dict)
        self.assertIsNotNone(packet.created_time)
        self.assertEqual(packet.status, "pending")
    
    def test_node_packet_execution_tracking(self):
        """Test job execution tracking."""
        packet = OptimizerNodePacket(
            parameter_set=self.parameter_set,
            algorithm_config=self.algorithm_config
        )
        
        # Start execution
        packet.start_execution("worker-1")
        self.assertEqual(packet.worker_id, "worker-1")
        self.assertEqual(packet.status, "running")
        self.assertIsNotNone(packet.start_time)
        
        # Complete execution
        packet.complete_execution()
        self.assertEqual(packet.status, "completed")
        self.assertIsNotNone(packet.end_time)
        self.assertIsNotNone(packet.duration)
    
    def test_node_packet_retry_logic(self):
        """Test job retry logic."""
        packet = OptimizerNodePacket(
            parameter_set=self.parameter_set,
            algorithm_config=self.algorithm_config
        )
        
        # Fail execution
        packet.fail_execution("Test error")
        self.assertEqual(packet.status, "failed")
        self.assertEqual(packet.error_message, "Test error")
        self.assertTrue(packet.can_retry())
        
        # Retry
        packet.increment_retry()
        self.assertEqual(packet.status, "pending")
        self.assertIsNone(packet.error_message)
        self.assertEqual(packet.metadata.retry_count, 1)
    
    def test_node_packet_serialization(self):
        """Test packet serialization and deserialization."""
        packet = OptimizerNodePacket(
            parameter_set=self.parameter_set,
            algorithm_config=self.algorithm_config
        )
        
        # Serialize to dict
        packet_dict = packet.to_dict()
        self.assertIsInstance(packet_dict, dict)
        self.assertIn("job_metadata", packet_dict)
        self.assertIn("parameter_set", packet_dict)
        self.assertIn("algorithm_config", packet_dict)
        
        # Deserialize from dict
        new_packet = OptimizerNodePacket(
            parameter_set=self.parameter_set,
            algorithm_config=self.algorithm_config
        ).from_dict(packet_dict)
        
        self.assertEqual(new_packet.job_id, packet.job_id)
        self.assertEqual(new_packet.campaign_id, packet.campaign_id)
    
    def test_node_packet_factory(self):
        """Test node packet factory methods."""
        # Create single packet
        packet = NodePacketFactory.create_packet(
            parameter_set=self.parameter_set,
            algorithm_config=self.algorithm_config,
            campaign_id="test_campaign"
        )
        
        self.assertEqual(packet.campaign_id, "test_campaign")
        self.assertIsNotNone(packet.job_id)
        
        # Create batch packets
        parameter_sets = [self.parameter_set, self.parameter_set]
        packets = NodePacketFactory.create_batch_packets(
            parameter_sets=parameter_sets,
            algorithm_config=self.algorithm_config,
            campaign_id="test_campaign"
        )
        
        self.assertEqual(len(packets), 2)
        for packet in packets:
            self.assertEqual(packet.campaign_id, "test_campaign")


class TestWorkerManager(unittest.TestCase):
    """Test worker manager functionality."""
    
    def setUp(self):
        self.worker_manager = LocalWorkerManager(max_workers=2)
        self.parameter_set = OptimizationParameterSet()
        self.parameter_set.add_parameter("param1", 10.0)
        
        self.algorithm_config = AlgorithmConfiguration(
            algorithm_type_name="TestAlgorithm",
            algorithm_location="test_algorithm.py",
            start_date="2020-01-01",
            end_date="2021-01-01"
        )
        
        self.packet = OptimizerNodePacket(
            parameter_set=self.parameter_set,
            algorithm_config=self.algorithm_config
        )
    
    async def test_worker_lifecycle(self):
        """Test worker start and stop lifecycle."""
        # Start workers
        success = await self.worker_manager.start_workers(2)
        self.assertTrue(success)
        self.assertEqual(self.worker_manager.get_worker_count(), 2)
        self.assertEqual(self.worker_manager.get_active_workers(), 2)
        
        # Stop workers
        success = await self.worker_manager.stop_workers()
        self.assertTrue(success)
    
    async def test_job_submission(self):
        """Test job submission and execution."""
        await self.worker_manager.start_workers(1)
        
        try:
            # Submit job
            job_id = await self.worker_manager.submit_job(self.packet)
            self.assertIsNotNone(job_id)
            
            # Wait for result (with timeout)
            max_wait = 10  # 10 seconds
            start_time = time.time()
            result = None
            
            while time.time() - start_time < max_wait:
                result = await self.worker_manager.get_job_result(job_id)
                if result is not None:
                    break
                await asyncio.sleep(0.1)
            
            self.assertIsNotNone(result)
            self.assertIsInstance(result, OptimizationResult)
        
        finally:
            await self.worker_manager.stop_workers()
    
    def test_worker_status_tracking(self):
        """Test worker status tracking."""
        # Initially no workers
        self.assertEqual(self.worker_manager.get_worker_count(), 0)
        self.assertEqual(self.worker_manager.get_active_workers(), 0)
        
        # Get status
        status = self.worker_manager.get_worker_status()
        self.assertIsInstance(status, dict)
        self.assertEqual(len(status), 0)


class TestResultCoordinator(unittest.TestCase):
    """Test result coordinator functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.coordinator = ResultCoordinator(
            campaign_id="test_campaign",
            output_folder=self.temp_dir
        )
        
        self.parameter_set = OptimizationParameterSet()
        self.parameter_set.add_parameter("param1", 10.0)
        
        self.metrics = PerformanceMetrics(
            total_return=0.15,
            sharpe_ratio=1.2,
            max_drawdown=0.08,
            win_rate=0.55
        )
        
        self.result = OptimizationResult(
            parameter_set=self.parameter_set,
            performance_metrics=self.metrics,
            fitness_score=1.2,
            execution_time=1.0,
            timestamp=datetime.now(timezone.utc),
            success=True
        )
    
    async def test_result_registration(self):
        """Test result registration."""
        await self.coordinator.register_result(self.result)
        
        all_results = await self.coordinator.get_all_results()
        self.assertEqual(len(all_results), 1)
        self.assertEqual(all_results[0], self.result)
        
        best_results = await self.coordinator.get_best_results(count=1)
        self.assertEqual(len(best_results), 1)
        self.assertEqual(best_results[0], self.result)
    
    async def test_result_export(self):
        """Test result export functionality."""
        await self.coordinator.register_result(self.result)
        
        # Export to JSON
        json_file = Path(self.temp_dir, "results.json")
        success = await self.coordinator.export_results(str(json_file), format="json")
        self.assertTrue(success)
        self.assertTrue(json_file.exists())
        
        # Verify JSON content
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        self.assertIn("campaign_id", data)
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 1)
        
        # Export to CSV
        csv_file = Path(self.temp_dir, "results.csv")
        success = await self.coordinator.export_results(str(csv_file), format="csv")
        self.assertTrue(success)
        self.assertTrue(csv_file.exists())
    
    def test_statistics_calculation(self):
        """Test statistics calculation."""
        # Initially no statistics
        stats = self.coordinator.get_statistics()
        self.assertEqual(stats.total_evaluations, 0)
        
        # Add result and check statistics
        asyncio.run(self.coordinator.register_result(self.result))
        
        stats = self.coordinator.get_statistics()
        self.assertEqual(stats.total_evaluations, 1)
        self.assertEqual(stats.successful_evaluations, 1)
        self.assertEqual(stats.best_fitness, 1.2)
    
    def test_real_time_metrics(self):
        """Test real-time metrics."""
        metrics = self.coordinator.get_real_time_metrics()
        self.assertIsInstance(metrics, dict)
        self.assertIn('total_evaluations', metrics)
        self.assertIn('successful_evaluations', metrics)
        self.assertIn('success_rate', metrics)
        self.assertIn('best_fitness', metrics)


class TestProgressReporter(unittest.TestCase):
    """Test progress reporter functionality."""
    
    def setUp(self):
        self.reporter = ProgressReporter()
        self.config = OptimizerLauncherConfiguration(
            optimization_target="sharpe_ratio",
            algorithm_type_name="TestAlgorithm",
            algorithm_location="test_algorithm.py",
            parameter_file="test_params.json"
        )
    
    def test_progress_reporting(self):
        """Test progress reporting methods."""
        # These should not raise exceptions
        self.reporter.report_campaign_start(self.config)
        self.reporter.report_progress_update(50, 100, 1.5, 30.0)
        self.reporter.report_worker_status_change("worker-1", WorkerStatus.BUSY)
        
        # Create mock result for reporting
        parameter_set = OptimizationParameterSet()
        metrics = PerformanceMetrics()
        result = OptimizationResult(
            parameter_set=parameter_set,
            performance_metrics=metrics,
            fitness_score=1.0,
            execution_time=1.0,
            timestamp=datetime.now(timezone.utc),
            success=True
        )
        
        self.reporter.report_result_received(result)
        self.reporter.report_error(ValueError("Test error"), {"context": "test"})


class TestOptimizerLauncher(unittest.TestCase):
    """Test main optimizer launcher functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.launcher = OptimizerLauncher()
        
        # Create test files
        self.algorithm_file = Path(self.temp_dir, "test_algorithm.py")
        self.algorithm_file.touch()
        
        self.params_file = Path(self.temp_dir, "test_params.json")
        with open(self.params_file, 'w') as f:
            json.dump({"parameters": []}, f)
        
        self.data_dir = Path(self.temp_dir, "data")
        self.data_dir.mkdir()
        
        self.config = OptimizerLauncherConfiguration(
            optimization_target="sharpe_ratio",
            algorithm_type_name="TestAlgorithm",
            algorithm_location=str(self.algorithm_file),
            parameter_file=str(self.params_file),
            mode=OptimizerLauncherMode.LOCAL,
            max_concurrent_backtests=2,
            data_folder=str(self.data_dir),
            output_folder=self.temp_dir
        )
    
    def test_launcher_initialization(self):
        """Test launcher initialization."""
        success = self.launcher.initialize(self.config)
        self.assertTrue(success)
        self.assertEqual(self.launcher.status, OptimizerLauncherStatus.OPTIMIZING)
        self.assertIsNotNone(self.launcher._campaign_id)
    
    def test_launcher_status_and_progress(self):
        """Test launcher status and progress tracking."""
        # Initial status
        self.assertEqual(self.launcher.status, OptimizerLauncherStatus.INITIALIZING)
        self.assertEqual(self.launcher.progress, 0.0)
        
        # After initialization
        self.launcher.initialize(self.config)
        self.assertNotEqual(self.launcher.status, OptimizerLauncherStatus.INITIALIZING)
    
    async def test_launcher_live_results(self):
        """Test getting live results."""
        self.launcher.initialize(self.config)
        
        results = await self.launcher.get_live_results()
        self.assertIsInstance(results, list)
    
    def test_launcher_stop(self):
        """Test launcher stop functionality."""
        self.launcher.initialize(self.config)
        
        success = self.launcher.stop_optimization()
        self.assertTrue(success)
        self.assertEqual(self.launcher.status, OptimizerLauncherStatus.CANCELLED)


class TestOptimizerLauncherFactory(unittest.TestCase):
    """Test optimizer launcher factory."""
    
    def test_create_launcher(self):
        """Test creating launcher instances."""
        launcher = OptimizerLauncherFactory.create_launcher(OptimizerLauncherMode.LOCAL)
        self.assertIsInstance(launcher, OptimizerLauncher)
    
    def test_create_from_environment(self):
        """Test creating launcher from environment."""
        with patch.dict('os.environ', {
            'OPTIMIZER_TARGET': 'sharpe_ratio',
            'ALGORITHM_TYPE_NAME': 'TestAlgorithm',
            'ALGORITHM_LOCATION': 'test.py',
            'PARAMETER_FILE': 'params.json'
        }):
            # This will fail validation but tests the creation process
            with self.assertRaises(Exception):
                OptimizerLauncherFactory.create_from_environment()


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete optimizer launcher system."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test configuration
        self.config = (OptimizerLauncherConfigurationBuilder()
                      .with_algorithm("TestAlgorithm", "test_algorithm.py")
                      .with_parameters("test_params.json")
                      .with_mode(OptimizerLauncherMode.LOCAL)
                      .with_concurrent_backtests(2)
                      .with_data_folder(self.temp_dir)
                      .with_output_folder(self.temp_dir)
                      .build())
    
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end optimization workflow."""
        # This is a simplified integration test
        # In a real scenario, this would run a complete optimization
        
        launcher = OptimizerLauncher()
        
        # Mock the components to avoid actual execution
        with patch.object(launcher, '_create_optimizer'), \
             patch.object(launcher, '_create_worker_manager'), \
             patch.object(launcher, '_load_parameter_space'):
            
            success = launcher.initialize(self.config)
            self.assertTrue(success)
            
            # Test status tracking
            self.assertIsNotNone(launcher.status)
            self.assertIsInstance(launcher.progress, float)


if __name__ == '__main__':
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTest(unittest.makeSuite(TestOptimizerLauncherConfiguration))
    suite.addTest(unittest.makeSuite(TestOptimizerNodePacket))
    suite.addTest(unittest.makeSuite(TestWorkerManager))
    suite.addTest(unittest.makeSuite(TestResultCoordinator))
    suite.addTest(unittest.makeSuite(TestProgressReporter))
    suite.addTest(unittest.makeSuite(TestOptimizerLauncher))
    suite.addTest(unittest.makeSuite(TestOptimizerLauncherFactory))
    suite.addTest(unittest.makeSuite(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\nTest Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")