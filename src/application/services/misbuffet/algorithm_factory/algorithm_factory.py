"""
Core algorithm factory for creating and managing algorithm instances.
"""

import os
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional, Type, List
from datetime import datetime

from ..common.interfaces import IAlgorithmFactory, IAlgorithm
from ..common.enums import Language
from .algorithm_loader import (
    BaseAlgorithmLoader, PythonAlgorithmLoader, FileAlgorithmLoader,
    ModuleAlgorithmLoader, SourceCodeLoader
)
from .compiler import PythonCompiler, CompilerResults
from .algorithm_node_packet import AlgorithmNodePacket


class AlgorithmFactory(IAlgorithmFactory):
    """
    Factory for creating algorithm instances.
    Handles loading, compilation, and instantiation of algorithms.
    """
    
    def __init__(self):
        self._loaders: Dict[Language, BaseAlgorithmLoader] = {}
        self._compilers: Dict[Language, PythonCompiler] = {}
        self._algorithm_cache: Dict[str, Type[IAlgorithm]] = {}
        
        # Initialize default loaders and compilers
        self._initialize_default_components()
    
    def _initialize_default_components(self):
        """Initialize default loaders and compilers."""
        # Python loader
        python_loader = PythonAlgorithmLoader()
        self._loaders[Language.PYTHON] = python_loader
        
        # Python compiler
        python_compiler = PythonCompiler()
        self._compilers[Language.PYTHON] = python_compiler
    
    def create_algorithm_instance(self, algorithm_name: str, **kwargs) -> IAlgorithm:
        """
        Create an instance of the specified algorithm.
        
        Args:
            algorithm_name: Name or identifier of the algorithm
            **kwargs: Additional parameters for algorithm creation
        
        Returns:
            Instance of the algorithm
        """
        language = kwargs.get('language', Language.PYTHON)
        
        try:
            # Check cache first
            cache_key = f"{algorithm_name}_{language.value}"
            if cache_key in self._algorithm_cache:
                algorithm_class = self._algorithm_cache[cache_key]
                return algorithm_class()
            
            # Load algorithm class
            algorithm_class = self._load_algorithm_class(algorithm_name, language, **kwargs)
            
            if algorithm_class:
                # Cache the class
                self._algorithm_cache[cache_key] = algorithm_class
                
                # Create instance
                return algorithm_class()
            else:
                raise RuntimeError(f"Failed to load algorithm class: {algorithm_name}")
                
        except Exception as e:
            raise RuntimeError(f"Failed to create algorithm instance '{algorithm_name}': {e}")
    
    def load_algorithm(self, path: str) -> IAlgorithm:
        """
        Load an algorithm from the specified path.
        
        Args:
            path: Path to the algorithm file or module
            
        Returns:
            Instance of the loaded algorithm
        """
        path_obj = Path(path)
        
        if not path_obj.exists():
            raise FileNotFoundError(f"Algorithm path does not exist: {path}")
        
        try:
            if path_obj.is_file():
                # Load from file
                return self._load_algorithm_from_file(path_obj)
            elif path_obj.is_dir():
                # Load from directory (package)
                return self._load_algorithm_from_package(path_obj)
            else:
                raise ValueError(f"Invalid algorithm path: {path}")
                
        except Exception as e:
            raise RuntimeError(f"Failed to load algorithm from '{path}': {e}")
    
    def load_algorithm_from_source(self, source_code: str, algorithm_name: str = "CustomAlgorithm") -> IAlgorithm:
        """
        Load an algorithm from source code string.
        
        Args:
            source_code: Python source code containing the algorithm
            algorithm_name: Name for the algorithm class
            
        Returns:
            Instance of the algorithm
        """
        try:
            # Use source code loader
            loader = SourceCodeLoader()
            algorithm_class = loader.load_from_source(source_code, algorithm_name)
            
            if algorithm_class:
                return algorithm_class()
            else:
                raise RuntimeError("Failed to load algorithm from source code")
                
        except Exception as e:
            raise RuntimeError(f"Failed to load algorithm from source: {e}")
    
    def compile_algorithm(self, source_path: str, output_path: str = None, 
                         language: Language = Language.PYTHON) -> CompilerResults:
        """
        Compile an algorithm from source code.
        
        Args:
            source_path: Path to source code
            output_path: Optional output path for compiled code
            language: Programming language
            
        Returns:
            Compilation results
        """
        if language not in self._compilers:
            raise ValueError(f"No compiler available for language: {language}")
        
        compiler = self._compilers[language]
        return compiler.compile(source_path, output_path)
    
    def _load_algorithm_class(self, algorithm_name: str, language: Language, **kwargs) -> Optional[Type[IAlgorithm]]:
        """Load algorithm class using appropriate loader."""
        if language not in self._loaders:
            raise ValueError(f"No loader available for language: {language}")
        
        loader = self._loaders[language]
        
        # Try different loading methods based on provided parameters
        file_path = kwargs.get('file_path')
        module_path = kwargs.get('module_path')
        source_code = kwargs.get('source_code')
        
        if source_code:
            # Load from source code
            if isinstance(loader, SourceCodeLoader):
                return loader.load_from_source(source_code, algorithm_name)
            else:
                source_loader = SourceCodeLoader()
                return source_loader.load_from_source(source_code, algorithm_name)
        
        elif file_path:
            # Load from file
            return loader.load_from_file(file_path, algorithm_name)
        
        elif module_path:
            # Load from module
            return loader.load_from_module(module_path, algorithm_name)
        
        else:
            # Try to find algorithm by name
            return self._find_algorithm_by_name(algorithm_name, loader)
    
    def _load_algorithm_from_file(self, file_path: Path) -> IAlgorithm:
        """Load algorithm from a single file."""
        if file_path.suffix.lower() != '.py':
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
        
        loader = FileAlgorithmLoader()
        algorithm_class = loader.load_from_file(str(file_path))
        
        if algorithm_class:
            return algorithm_class()
        else:
            raise RuntimeError(f"No algorithm class found in file: {file_path}")
    
    def _load_algorithm_from_package(self, package_path: Path) -> IAlgorithm:
        """Load algorithm from a package directory."""
        # Look for __init__.py or main.py
        init_file = package_path / "__init__.py"
        main_file = package_path / "main.py"
        
        target_file = None
        if init_file.exists():
            target_file = init_file
        elif main_file.exists():
            target_file = main_file
        else:
            # Look for any .py file with a class that inherits from IAlgorithm
            python_files = list(package_path.glob("*.py"))
            if python_files:
                target_file = python_files[0]  # Use first Python file
            else:
                raise RuntimeError(f"No Python files found in package: {package_path}")
        
        return self._load_algorithm_from_file(target_file)
    
    def _find_algorithm_by_name(self, algorithm_name: str, loader: BaseAlgorithmLoader) -> Optional[Type[IAlgorithm]]:
        """Find algorithm class by name in common locations."""
        
        # Common algorithm locations to search
        search_paths = [
            f"algorithms.{algorithm_name.lower()}",
            f"strategies.{algorithm_name.lower()}",
            algorithm_name,
            f"algorithm.{algorithm_name}",
        ]
        
        for module_path in search_paths:
            try:
                algorithm_class = loader.load_from_module(module_path, algorithm_name)
                if algorithm_class:
                    return algorithm_class
            except Exception:
                continue  # Try next path
        
        return None
    
    def create_algorithm_from_packet(self, packet: AlgorithmNodePacket) -> IAlgorithm:
        """
        Create algorithm instance from an algorithm node packet.
        
        Args:
            packet: Algorithm configuration packet
            
        Returns:
            Configured algorithm instance
        """
        try:
            # Create algorithm instance
            algorithm = self.create_algorithm_instance(
                packet.algorithm_name,
                language=packet.language,
                file_path=packet.algorithm_file_path,
                source_code=packet.source_code
            )
            
            # Apply configuration from packet
            self._configure_algorithm_from_packet(algorithm, packet)
            
            return algorithm
            
        except Exception as e:
            raise RuntimeError(f"Failed to create algorithm from packet: {e}")
    
    def _configure_algorithm_from_packet(self, algorithm: IAlgorithm, packet: AlgorithmNodePacket):
        """Configure algorithm instance with packet parameters."""
        # Set basic properties
        if hasattr(algorithm, 'set_start_date') and packet.start_date:
            algorithm.set_start_date(
                packet.start_date.year,
                packet.start_date.month,
                packet.start_date.day
            )
        
        if hasattr(algorithm, 'set_end_date') and packet.end_date:
            algorithm.set_end_date(
                packet.end_date.year,
                packet.end_date.month,
                packet.end_date.day
            )
        
        if hasattr(algorithm, 'set_cash') and packet.starting_capital:
            algorithm.set_cash(packet.starting_capital)
        
        # Apply additional parameters
        if packet.parameters:
            for key, value in packet.parameters.items():
                if hasattr(algorithm, key):
                    setattr(algorithm, key, value)
    
    def register_loader(self, language: Language, loader: BaseAlgorithmLoader):
        """Register a custom algorithm loader for a language."""
        self._loaders[language] = loader
    
    def register_compiler(self, language: Language, compiler: PythonCompiler):
        """Register a custom compiler for a language."""
        self._compilers[language] = compiler
    
    def clear_cache(self):
        """Clear the algorithm class cache."""
        self._algorithm_cache.clear()
    
    def get_available_algorithms(self, search_paths: List[str] = None) -> List[str]:
        """
        Get list of available algorithms in search paths.
        
        Args:
            search_paths: Optional list of paths to search
            
        Returns:
            List of algorithm names
        """
        algorithms = []
        
        if search_paths is None:
            search_paths = ['algorithms', 'strategies', '.']
        
        for search_path in search_paths:
            try:
                path_obj = Path(search_path)
                if path_obj.exists() and path_obj.is_dir():
                    # Find Python files
                    for py_file in path_obj.glob("*.py"):
                        if py_file.name != "__init__.py":
                            algorithm_name = py_file.stem
                            algorithms.append(algorithm_name)
                            
            except Exception as e:
                print(f"Error searching path {search_path}: {e}")
        
        return sorted(list(set(algorithms)))  # Remove duplicates and sort
    
    def validate_algorithm(self, algorithm: IAlgorithm) -> List[str]:
        """
        Validate an algorithm instance and return list of issues.
        
        Args:
            algorithm: Algorithm instance to validate
            
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        # Check required methods
        required_methods = ['initialize', 'on_data']
        for method in required_methods:
            if not hasattr(algorithm, method):
                issues.append(f"Missing required method: {method}")
            elif not callable(getattr(algorithm, method)):
                issues.append(f"Method is not callable: {method}")
        
        # Check if algorithm is properly subclassed
        if not isinstance(algorithm, IAlgorithm):
            issues.append("Algorithm does not implement IAlgorithm interface")
        
        # Additional validation could be added here
        
        return issues
    
    def get_algorithm_info(self, algorithm_name: str, **kwargs) -> Dict[str, Any]:
        """
        Get information about an algorithm without instantiating it.
        
        Args:
            algorithm_name: Name of the algorithm
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with algorithm information
        """
        try:
            language = kwargs.get('language', Language.PYTHON)
            algorithm_class = self._load_algorithm_class(algorithm_name, language, **kwargs)
            
            if algorithm_class:
                info = {
                    'name': algorithm_name,
                    'class_name': algorithm_class.__name__,
                    'module': algorithm_class.__module__,
                    'language': language.value,
                    'docstring': algorithm_class.__doc__,
                    'methods': [method for method in dir(algorithm_class) 
                              if not method.startswith('_') and callable(getattr(algorithm_class, method))],
                }
                
                return info
            else:
                return {'error': f"Algorithm class not found: {algorithm_name}"}
                
        except Exception as e:
            return {'error': f"Failed to get algorithm info: {e}"}
    
    def __str__(self) -> str:
        """String representation of the algorithm factory."""
        return (f"AlgorithmFactory(loaders={len(self._loaders)}, "
                f"cached_algorithms={len(self._algorithm_cache)})")


# Global algorithm factory instance
_algorithm_factory = AlgorithmFactory()


def get_algorithm_factory() -> AlgorithmFactory:
    """Get the global algorithm factory instance."""
    return _algorithm_factory