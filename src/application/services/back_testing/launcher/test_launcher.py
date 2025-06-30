"""
QuantConnect Lean Launcher Unit Tests

Comprehensive test suite for the launcher module including configuration,
command-line parsing, handlers, and main launcher functionality.
"""

import unittest
import tempfile
import json
import os
import logging
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typing import Dict, Any

from .interfaces import (
    LauncherConfiguration,
    LauncherMode,
    LauncherStatus,
    ConfigurationException,
    HandlerCreationException,
    EngineInitializationException,
    AlgorithmLoadException
)
from .configuration import ConfigurationProvider, ConfigurationBuilder, ConfigurationValidator
from .command_line import CommandLineParser, CommandLineArgumentProcessor
from .handlers import HandlerFactory, LauncherSystemHandlers, LauncherAlgorithmHandlers
from .launcher import Launcher, LauncherLogger, main


class TestLauncherConfiguration(unittest.TestCase):
    """Test cases for LauncherConfiguration."""
    
    def test_launcher_configuration_creation(self):
        """Test creating LauncherConfiguration."""
        config = LauncherConfiguration(
            mode=LauncherMode.BACKTESTING,
            algorithm_type_name="TestAlgorithm",
            algorithm_location="./test_algorithm.py",
            data_folder="./data"
        )
        
        self.assertEqual(config.mode, LauncherMode.BACKTESTING)
        self.assertEqual(config.algorithm_type_name, "TestAlgorithm")
        self.assertEqual(config.algorithm_location, "./test_algorithm.py")
        self.assertEqual(config.data_folder, "./data")
        self.assertEqual(config.environment, "backtesting")
        self.assertFalse(config.live_mode)
        self.assertIsInstance(config.custom_config, dict)
    
    def test_launcher_configuration_post_init(self):
        """Test LauncherConfiguration post_init behavior."""
        config = LauncherConfiguration(
            mode=LauncherMode.LIVE_TRADING,
            algorithm_type_name="TestAlgorithm",
            algorithm_location="./test_algorithm.py",
            data_folder="./data",
            custom_config=None
        )
        
        self.assertIsInstance(config.custom_config, dict)
        self.assertEqual(len(config.custom_config), 0)


class TestConfigurationProvider(unittest.TestCase):
    """Test cases for ConfigurationProvider."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config_provider = ConfigurationProvider()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_default_configuration(self):
        """Test loading default configuration."""
        config = self.config_provider.load_configuration()
        
        self.assertIsInstance(config, LauncherConfiguration)
        self.assertEqual(config.environment, "backtesting")
        self.assertEqual(config.log_handler, "ConsoleLogHandler")
        self.assertFalse(config.live_mode)
    
    def test_load_json_configuration(self):
        """Test loading configuration from JSON file."""
        config_data = {
            "environment": "live",
            "algorithm-type-name": "MyAlgorithm",
            "algorithm-location": "./my_algorithm.py",
            "data-folder": "./my_data/",
            "live-mode": True,
            "debugging": True
        }
        
        config_file = Path(self.temp_dir) / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        config = self.config_provider.load_configuration(str(config_file))
        
        self.assertEqual(config.mode, LauncherMode.LIVE_TRADING)
        self.assertEqual(config.algorithm_type_name, "MyAlgorithm")
        self.assertEqual(config.algorithm_location, "./my_algorithm.py")
        self.assertEqual(config.data_folder, "./my_data/")
        self.assertTrue(config.live_mode)
        self.assertTrue(config.debugging)
    
    def test_load_invalid_json_configuration(self):
        """Test loading invalid JSON configuration."""
        config_file = Path(self.temp_dir) / "invalid_config.json"
        with open(config_file, 'w') as f:
            f.write("{ invalid json }")
        
        with self.assertRaises(ConfigurationException):
            self.config_provider.load_configuration(str(config_file))
    
    def test_load_nonexistent_configuration(self):
        """Test loading nonexistent configuration file."""
        with self.assertRaises(ConfigurationException):
            self.config_provider.load_configuration("nonexistent.json")
    
    @patch.dict(os.environ, {
        'LEAN_ALGORITHM_TYPE_NAME': 'EnvAlgorithm',
        'LEAN_LIVE_MODE': 'true',
        'LEAN_DEBUGGING': 'false'
    })
    def test_load_environment_configuration(self):
        """Test loading configuration from environment variables."""
        config = self.config_provider.load_configuration()
        
        self.assertEqual(config.algorithm_type_name, "EnvAlgorithm")
        self.assertTrue(config.live_mode)
        self.assertFalse(config.debugging)
    
    def test_validate_configuration_success(self):
        """Test successful configuration validation."""
        config = LauncherConfiguration(
            mode=LauncherMode.BACKTESTING,
            algorithm_type_name="TestAlgorithm",
            algorithm_location="./test_algorithm.py",
            data_folder=str(Path(self.temp_dir))
        )
        
        errors = self.config_provider.validate_configuration(config)
        self.assertEqual(len(errors), 0)
    
    def test_validate_configuration_errors(self):
        """Test configuration validation with errors."""
        config = LauncherConfiguration(
            mode=LauncherMode.BACKTESTING,
            algorithm_type_name="",
            algorithm_location="",
            data_folder="",
            maximum_data_points_per_chart_series=-1
        )
        
        errors = self.config_provider.validate_configuration(config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Algorithm type name is required" in error for error in errors))
        self.assertTrue(any("Algorithm location is required" in error for error in errors))
    
    def test_save_configuration(self):
        """Test saving configuration to JSON file."""
        config = LauncherConfiguration(
            mode=LauncherMode.BACKTESTING,
            algorithm_type_name="TestAlgorithm",
            algorithm_location="./test_algorithm.py",
            data_folder="./data"
        )
        
        output_file = Path(self.temp_dir) / "output_config.json"
        self.config_provider.save_configuration(config, str(output_file))
        
        self.assertTrue(output_file.exists())
        
        # Verify saved content
        with open(output_file) as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data["algorithm-type-name"], "TestAlgorithm")
        self.assertEqual(saved_data["algorithm-location"], "./test_algorithm.py")
        self.assertEqual(saved_data["data-folder"], "./data")


class TestConfigurationBuilder(unittest.TestCase):
    """Test cases for ConfigurationBuilder."""
    
    def test_builder_pattern(self):
        """Test configuration builder pattern."""
        config = (ConfigurationBuilder()
                 .with_algorithm("MyAlgorithm", "./my_algorithm.py")
                 .with_data_folder("./my_data")
                 .with_environment("live")
                 .with_live_mode(True)
                 .with_debugging(True)
                 .with_custom_config("custom_key", "custom_value")
                 .build())
        
        self.assertEqual(config.algorithm_type_name, "MyAlgorithm")
        self.assertEqual(config.algorithm_location, "./my_algorithm.py")
        self.assertEqual(config.data_folder, "./my_data")
        self.assertEqual(config.environment, "live")
        self.assertTrue(config.live_mode)
        self.assertTrue(config.debugging)
        self.assertEqual(config.custom_config["custom_key"], "custom_value")


class TestCommandLineParser(unittest.TestCase):
    """Test cases for CommandLineParser."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = CommandLineParser()
    
    def test_parse_basic_arguments(self):
        """Test parsing basic arguments."""
        args = [
            "--algorithm-type-name", "TestAlgorithm",
            "--algorithm-location", "./test_algorithm.py"
        ]
        
        result = self.parser.parse_arguments(args)
        
        self.assertEqual(result["algorithm_type_name"], "TestAlgorithm")
        self.assertEqual(result["algorithm_location"], "./test_algorithm.py")
    
    def test_parse_all_arguments(self):
        """Test parsing all possible arguments."""
        args = [
            "--config", "./config.json",
            "--algorithm-type-name", "TestAlgorithm",
            "--algorithm-location", "./test_algorithm.py",
            "--data-folder", "./data",
            "--environment", "backtesting",
            "--live-mode",
            "--debugging",
            "--log-handler", "FileLogHandler",
            "--maximum-data-points-per-chart-series", "5000",
            "--maximum-chart-series", "50",
            "--show-missing-data-logs",
            "--verbose", "--verbose"
        ]
        
        result = self.parser.parse_arguments(args)
        
        self.assertEqual(result["algorithm_type_name"], "TestAlgorithm")
        self.assertTrue(result["live_mode"])
        self.assertTrue(result["debugging"])
        self.assertEqual(result["maximum_data_points_per_chart_series"], 5000)
        self.assertEqual(result["maximum_chart_series"], 50)
        self.assertTrue(result["show_missing_data_logs"])
        self.assertEqual(result["verbose"], 2)
    
    def test_parse_conflicting_arguments(self):
        """Test parsing conflicting arguments."""
        args = [
            "--show-missing-data-logs",
            "--no-missing-data-logs"
        ]
        
        with self.assertRaises(ConfigurationException):
            self.parser.parse_arguments(args)
    
    def test_get_help_text(self):
        """Test getting help text."""
        help_text = self.parser.get_help_text()
        
        self.assertIsInstance(help_text, str)
        self.assertIn("QuantConnect Lean Launcher", help_text)
        self.assertIn("--algorithm-type-name", help_text)


class TestHandlerFactory(unittest.TestCase):
    """Test cases for HandlerFactory."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.factory = HandlerFactory()
        self.config = LauncherConfiguration(
            mode=LauncherMode.BACKTESTING,
            algorithm_type_name="TestAlgorithm",
            algorithm_location="./test_algorithm.py",
            data_folder="./data"
        )
    
    def test_create_system_handlers(self):
        """Test creating system handlers."""
        handlers = self.factory.create_system_handlers(self.config)
        
        self.assertIsInstance(handlers, LauncherSystemHandlers)
        self.assertIsNotNone(handlers.log_handler)
        self.assertIsNotNone(handlers.messaging_handler)
        self.assertIsNotNone(handlers.job_queue_handler)
        self.assertIsNotNone(handlers.api_handler)
    
    def test_create_algorithm_handlers(self):
        """Test creating algorithm handlers."""
        handlers = self.factory.create_algorithm_handlers(self.config)
        
        self.assertIsInstance(handlers, LauncherAlgorithmHandlers)
        self.assertIsNotNone(handlers.data_feed)
        self.assertIsNotNone(handlers.setup_handler)
        self.assertIsNotNone(handlers.real_time_handler)
        self.assertIsNotNone(handlers.result_handler)
        self.assertIsNotNone(handlers.transaction_handler)
    
    def test_create_handlers_for_live_mode(self):
        """Test creating handlers for live mode."""
        live_config = LauncherConfiguration(
            mode=LauncherMode.LIVE_TRADING,
            algorithm_type_name="TestAlgorithm",
            algorithm_location="./test_algorithm.py",
            data_folder="./data",
            live_mode=True
        )
        
        handlers = self.factory.create_algorithm_handlers(live_config)
        
        self.assertIsInstance(handlers, LauncherAlgorithmHandlers)
        # In live mode, different handlers should be created
        self.assertIsNotNone(handlers.data_feed)


class TestLauncher(unittest.TestCase):
    """Test cases for Launcher."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger("test")
        self.launcher = Launcher(self.logger)
        self.config = LauncherConfiguration(
            mode=LauncherMode.BACKTESTING,
            algorithm_type_name="TestAlgorithm",
            algorithm_location="./test_algorithm.py",
            data_folder="./data"
        )
    
    @patch('src.application.services.back_testing.launcher.launcher.HandlerFactory')
    @patch('src.application.services.back_testing.launcher.launcher.LeanEngine')
    @patch('src.application.services.back_testing.launcher.launcher.AlgorithmFactory')
    def test_initialize_success(self, mock_algorithm_factory, mock_engine, mock_handler_factory):
        """Test successful launcher initialization."""
        # Setup mocks
        mock_handler_factory.return_value.create_system_handlers.return_value = Mock()
        mock_handler_factory.return_value.create_algorithm_handlers.return_value = Mock()
        mock_engine.return_value = Mock()
        mock_algorithm_factory.return_value.create_algorithm_instance.return_value = Mock()
        
        # Test initialization
        result = self.launcher.initialize(self.config)
        
        self.assertTrue(result)
        self.assertEqual(self.launcher.status, LauncherStatus.RUNNING)
    
    def test_initialize_invalid_config(self):
        """Test initialization with invalid configuration."""
        invalid_config = LauncherConfiguration(
            mode=LauncherMode.BACKTESTING,
            algorithm_type_name="",
            algorithm_location="",
            data_folder=""
        )
        
        result = self.launcher.initialize(invalid_config)
        
        self.assertFalse(result)
        self.assertEqual(self.launcher.status, LauncherStatus.FAILED)
    
    @patch('src.application.services.back_testing.launcher.launcher.HandlerFactory')
    @patch('src.application.services.back_testing.launcher.launcher.LeanEngine')
    @patch('src.application.services.back_testing.launcher.launcher.AlgorithmFactory')
    def test_run_success(self, mock_algorithm_factory, mock_engine, mock_handler_factory):
        """Test successful launcher run."""
        # Setup mocks
        mock_handler_factory.return_value.create_system_handlers.return_value = Mock()
        mock_handler_factory.return_value.create_algorithm_handlers.return_value = Mock()
        mock_engine_instance = Mock()
        mock_engine_instance.run.return_value = True
        mock_engine.return_value = mock_engine_instance
        mock_algorithm_factory.return_value.create_algorithm_instance.return_value = Mock()
        
        # Initialize and run
        self.launcher.initialize(self.config)
        result = self.launcher.run()
        
        self.assertTrue(result)
        self.assertEqual(self.launcher.status, LauncherStatus.COMPLETED)
        mock_engine_instance.run.assert_called_once()
    
    def test_run_without_initialization(self):
        """Test running launcher without initialization."""
        result = self.launcher.run()
        
        self.assertFalse(result)
        self.assertEqual(self.launcher.status, LauncherStatus.FAILED)
    
    def test_stop(self):
        """Test stopping launcher."""
        result = self.launcher.stop()
        
        self.assertTrue(result)
        self.assertEqual(self.launcher.status, LauncherStatus.COMPLETED)


class TestLauncherLogger(unittest.TestCase):
    """Test cases for LauncherLogger."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger("test")
        self.launcher_logger = LauncherLogger(self.logger)
        self.config = LauncherConfiguration(
            mode=LauncherMode.BACKTESTING,
            algorithm_type_name="TestAlgorithm",
            algorithm_location="./test_algorithm.py",
            data_folder="./data"
        )
    
    def test_log_initialization_start(self):
        """Test logging initialization start."""
        with patch.object(self.logger, 'info') as mock_info:
            self.launcher_logger.log_initialization_start(self.config)
            
            # Check that info was called multiple times
            self.assertGreater(mock_info.call_count, 5)
    
    def test_log_execution_complete(self):
        """Test logging execution completion."""
        with patch.object(self.logger, 'info') as mock_info:
            self.launcher_logger.log_execution_complete(True)
            
            mock_info.assert_called()
    
    def test_log_error(self):
        """Test logging errors."""
        with patch.object(self.logger, 'error') as mock_error:
            error = Exception("Test error")
            self.launcher_logger.log_error(error, "test context")
            
            mock_error.assert_called()


class TestMainFunction(unittest.TestCase):
    """Test cases for main function."""
    
    @patch('src.application.services.back_testing.launcher.launcher.Launcher')
    def test_main_with_valid_arguments(self, mock_launcher):
        """Test main function with valid arguments."""
        # Setup mock
        mock_launcher_instance = Mock()
        mock_launcher_instance.initialize.return_value = True
        mock_launcher_instance.run.return_value = True
        mock_launcher.return_value = mock_launcher_instance
        
        # Test main function
        result = main([
            "--algorithm-type-name", "TestAlgorithm",
            "--algorithm-location", "./test_algorithm.py"
        ])
        
        self.assertEqual(result, 0)
        mock_launcher_instance.initialize.assert_called_once()
        mock_launcher_instance.run.assert_called_once()
    
    def test_main_with_help_argument(self):
        """Test main function with help argument."""
        with self.assertRaises(SystemExit):
            main(["--help"])
    
    def test_main_with_validate_config(self):
        """Test main function with config validation."""
        result = main([
            "--algorithm-type-name", "TestAlgorithm",
            "--algorithm-location", "./test_algorithm.py",
            "--validate-config"
        ])
        
        self.assertEqual(result, 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for launcher components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_configuration_flow(self):
        """Test complete configuration loading and processing flow."""
        # Create config file
        config_data = {
            "environment": "backtesting",
            "algorithm-type-name": "TestAlgorithm",
            "algorithm-location": "./test_algorithm.py",
            "data-folder": "./data",
            "debugging": True
        }
        
        config_file = Path(self.temp_dir) / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Parse command-line arguments
        parser = CommandLineParser()
        args = parser.parse_arguments([
            "--config", str(config_file),
            "--live-mode"  # Override from command line
        ])
        
        # Load configuration
        config_provider = ConfigurationProvider()
        config = config_provider.load_configuration(str(config_file))
        
        # Apply command-line overrides
        processor = CommandLineArgumentProcessor()
        config_dict = {
            "algorithm-type-name": config.algorithm_type_name,
            "live-mode": config.live_mode
        }
        updated_config_dict = processor.apply_arguments_to_config(args, config_dict)
        
        # Verify overrides applied
        self.assertTrue(updated_config_dict["live-mode"])
        self.assertEqual(updated_config_dict["algorithm-type-name"], "TestAlgorithm")


if __name__ == '__main__':
    unittest.main()