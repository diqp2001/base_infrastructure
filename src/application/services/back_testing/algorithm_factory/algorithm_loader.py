"""
Algorithm loaders for different sources and formats.
"""

import ast
import sys
import types
import importlib
import importlib.util
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Type, Optional, List, Dict, Any
import inspect

from ..common.interfaces import IAlgorithm


class BaseAlgorithmLoader(ABC):
    """
    Abstract base class for algorithm loaders.
    """
    
    @abstractmethod
    def load_from_file(self, file_path: str, algorithm_name: str = None) -> Optional[Type[IAlgorithm]]:
        """Load algorithm class from a file."""
        pass
    
    @abstractmethod
    def load_from_module(self, module_path: str, algorithm_name: str = None) -> Optional[Type[IAlgorithm]]:
        """Load algorithm class from a module."""
        pass
    
    def supports_file_type(self, file_extension: str) -> bool:
        """Check if this loader supports the given file extension."""
        return file_extension.lower() == '.py'
    
    def _find_algorithm_classes(self, module: types.ModuleType) -> List[Type[IAlgorithm]]:
        """Find all algorithm classes in a module."""
        algorithm_classes = []
        
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Skip imported classes
            if obj.__module__ != module.__name__:
                continue
            
            # Check if class implements IAlgorithm interface
            if self._is_algorithm_class(obj):
                algorithm_classes.append(obj)
        
        return algorithm_classes
    
    def _is_algorithm_class(self, cls: Type) -> bool:
        """Check if a class is an algorithm class."""
        try:
            # Check if class inherits from IAlgorithm or has required methods
            if issubclass(cls, IAlgorithm):
                return True
            
            # Check for required algorithm methods
            required_methods = ['initialize', 'on_data']
            return all(hasattr(cls, method) and callable(getattr(cls, method)) 
                      for method in required_methods)
                      
        except TypeError:
            return False
    
    def _get_algorithm_class_by_name(self, module: types.ModuleType, algorithm_name: str) -> Optional[Type[IAlgorithm]]:
        """Get specific algorithm class by name from module."""
        if hasattr(module, algorithm_name):
            cls = getattr(module, algorithm_name)
            if inspect.isclass(cls) and self._is_algorithm_class(cls):
                return cls
        
        return None


class PythonAlgorithmLoader(BaseAlgorithmLoader):
    """
    Loader for Python algorithm files and modules.
    """
    
    def load_from_file(self, file_path: str, algorithm_name: str = None) -> Optional[Type[IAlgorithm]]:
        """Load algorithm class from a Python file."""
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Algorithm file not found: {file_path}")
        
        if not self.supports_file_type(file_path_obj.suffix):
            raise ValueError(f"Unsupported file type: {file_path_obj.suffix}")
        
        try:
            # Create module spec
            module_name = file_path_obj.stem
            spec = importlib.util.spec_from_file_location(module_name, file_path_obj)
            
            if spec is None or spec.loader is None:
                raise RuntimeError(f"Cannot create module spec for {file_path}")
            
            # Load module
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Find algorithm class
            if algorithm_name:
                algorithm_class = self._get_algorithm_class_by_name(module, algorithm_name)
                if algorithm_class:
                    return algorithm_class
                else:
                    raise RuntimeError(f"Algorithm class '{algorithm_name}' not found in {file_path}")
            else:
                # Return first algorithm class found
                algorithm_classes = self._find_algorithm_classes(module)
                if algorithm_classes:
                    return algorithm_classes[0]
                else:
                    raise RuntimeError(f"No algorithm classes found in {file_path}")
                    
        except Exception as e:
            raise RuntimeError(f"Failed to load algorithm from {file_path}: {e}")
    
    def load_from_module(self, module_path: str, algorithm_name: str = None) -> Optional[Type[IAlgorithm]]:
        """Load algorithm class from a Python module."""
        try:
            # Import the module
            module = importlib.import_module(module_path)
            
            # Find algorithm class
            if algorithm_name:
                algorithm_class = self._get_algorithm_class_by_name(module, algorithm_name)
                if algorithm_class:
                    return algorithm_class
                else:
                    raise RuntimeError(f"Algorithm class '{algorithm_name}' not found in module {module_path}")
            else:
                # Return first algorithm class found
                algorithm_classes = self._find_algorithm_classes(module)
                if algorithm_classes:
                    return algorithm_classes[0]
                else:
                    raise RuntimeError(f"No algorithm classes found in module {module_path}")
                    
        except ImportError as e:
            raise RuntimeError(f"Failed to import module {module_path}: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load algorithm from module {module_path}: {e}")


class FileAlgorithmLoader(PythonAlgorithmLoader):
    """
    Specialized loader for algorithm files with additional file handling capabilities.
    """
    
    def __init__(self):
        super().__init__()
        self._file_cache: Dict[str, types.ModuleType] = {}
    
    def load_from_file(self, file_path: str, algorithm_name: str = None) -> Optional[Type[IAlgorithm]]:
        """Load algorithm with file caching."""
        file_path_obj = Path(file_path)
        
        # Check cache first
        cache_key = str(file_path_obj.absolute())
        if cache_key in self._file_cache:
            module = self._file_cache[cache_key]
            
            if algorithm_name:
                return self._get_algorithm_class_by_name(module, algorithm_name)
            else:
                algorithm_classes = self._find_algorithm_classes(module)
                return algorithm_classes[0] if algorithm_classes else None
        
        # Load using parent implementation
        algorithm_class = super().load_from_file(file_path, algorithm_name)
        
        # Cache the module
        if algorithm_class:
            module_name = file_path_obj.stem
            if module_name in sys.modules:
                self._file_cache[cache_key] = sys.modules[module_name]
        
        return algorithm_class
    
    def clear_cache(self):
        """Clear the file cache."""
        self._file_cache.clear()
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get information about an algorithm file without loading it."""
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            return {'error': f"File not found: {file_path}"}
        
        try:
            # Parse file to find classes
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            classes = []
            functions = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if class might be an algorithm
                    base_names = [base.id for base in node.bases if isinstance(base, ast.Name)]
                    is_algorithm = any('Algorithm' in name for name in base_names)
                    
                    classes.append({
                        'name': node.name,
                        'line': node.lineno,
                        'is_algorithm': is_algorithm,
                        'docstring': ast.get_docstring(node)
                    })
                    
                elif isinstance(node, ast.FunctionDef):
                    functions.append({
                        'name': node.name,
                        'line': node.lineno,
                        'docstring': ast.get_docstring(node)
                    })
                    
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                        
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for alias in node.names:
                            imports.append(f"{node.module}.{alias.name}")
            
            return {
                'file_path': str(file_path_obj),
                'size_bytes': file_path_obj.stat().st_size,
                'classes': classes,
                'functions': functions,
                'imports': imports,
                'lines': len(source.splitlines())
            }
            
        except Exception as e:
            return {'error': f"Failed to analyze file: {e}"}


class ModuleAlgorithmLoader(PythonAlgorithmLoader):
    """
    Specialized loader for Python modules with package support.
    """
    
    def __init__(self):
        super().__init__()
        self._module_cache: Dict[str, types.ModuleType] = {}
    
    def load_from_module(self, module_path: str, algorithm_name: str = None) -> Optional[Type[IAlgorithm]]:
        """Load algorithm with module caching."""
        # Check cache first
        if module_path in self._module_cache:
            module = self._module_cache[module_path]
            
            if algorithm_name:
                return self._get_algorithm_class_by_name(module, algorithm_name)
            else:
                algorithm_classes = self._find_algorithm_classes(module)
                return algorithm_classes[0] if algorithm_classes else None
        
        # Load using parent implementation
        algorithm_class = super().load_from_module(module_path, algorithm_name)
        
        # Cache the module
        if algorithm_class and module_path in sys.modules:
            self._module_cache[module_path] = sys.modules[module_path]
        
        return algorithm_class
    
    def load_from_package(self, package_path: str, algorithm_name: str = None) -> Optional[Type[IAlgorithm]]:
        """Load algorithm from a package directory."""
        package_path_obj = Path(package_path)
        
        if not package_path_obj.exists() or not package_path_obj.is_dir():
            raise ValueError(f"Package path is not a valid directory: {package_path}")
        
        # Add package path to sys.path temporarily
        abs_package_path = str(package_path_obj.absolute())
        if abs_package_path not in sys.path:
            sys.path.insert(0, abs_package_path)
            try:
                # Try to import as package
                package_name = package_path_obj.name
                return self.load_from_module(package_name, algorithm_name)
            finally:
                sys.path.remove(abs_package_path)
        else:
            package_name = package_path_obj.name
            return self.load_from_module(package_name, algorithm_name)
    
    def discover_algorithms_in_package(self, package_path: str) -> List[Dict[str, Any]]:
        """Discover all algorithms in a package."""
        algorithms = []
        package_path_obj = Path(package_path)
        
        if not package_path_obj.exists() or not package_path_obj.is_dir():
            return algorithms
        
        # Search for Python files
        for py_file in package_path_obj.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            
            try:
                # Get relative module path
                relative_path = py_file.relative_to(package_path_obj)
                module_parts = [package_path_obj.name] + list(relative_path.with_suffix('').parts)
                module_path = '.'.join(module_parts)
                
                # Load module and find algorithms
                algorithm_classes = self._find_algorithm_classes_in_file(str(py_file))
                
                for algorithm_class in algorithm_classes:
                    algorithms.append({
                        'name': algorithm_class.__name__,
                        'module_path': module_path,
                        'file_path': str(py_file),
                        'docstring': algorithm_class.__doc__
                    })
                    
            except Exception as e:
                print(f"Error discovering algorithms in {py_file}: {e}")
        
        return algorithms
    
    def _find_algorithm_classes_in_file(self, file_path: str) -> List[Type[IAlgorithm]]:
        """Find algorithm classes in a specific file without importing."""
        try:
            loader = FileAlgorithmLoader()
            # This would load the file, but we'll use a simpler approach
            # by parsing the AST to avoid potential import issues
            return []  # Simplified for now
        except Exception:
            return []
    
    def clear_cache(self):
        """Clear the module cache."""
        self._module_cache.clear()


class SourceCodeLoader(BaseAlgorithmLoader):
    """
    Loader for algorithm source code provided as strings.
    """
    
    def __init__(self):
        super().__init__()
        self._source_cache: Dict[str, types.ModuleType] = {}
    
    def load_from_source(self, source_code: str, algorithm_name: str = "CustomAlgorithm") -> Optional[Type[IAlgorithm]]:
        """Load algorithm class from source code string."""
        try:
            # Create a unique module name
            module_name = f"algorithm_{hash(source_code) % 1000000}"
            
            # Check cache
            if module_name in self._source_cache:
                module = self._source_cache[module_name]
                algorithm_classes = self._find_algorithm_classes(module)
                return algorithm_classes[0] if algorithm_classes else None
            
            # Compile source code
            compiled_code = compile(source_code, f"<{module_name}>", 'exec')
            
            # Create module
            module = types.ModuleType(module_name)
            module.__file__ = f"<{module_name}>"
            
            # Execute code in module namespace
            exec(compiled_code, module.__dict__)
            
            # Add to sys.modules and cache
            sys.modules[module_name] = module
            self._source_cache[module_name] = module
            
            # Find algorithm class
            if hasattr(module, algorithm_name):
                cls = getattr(module, algorithm_name)
                if inspect.isclass(cls) and self._is_algorithm_class(cls):
                    return cls
            
            # If specific name not found, return first algorithm class
            algorithm_classes = self._find_algorithm_classes(module)
            if algorithm_classes:
                return algorithm_classes[0]
            else:
                raise RuntimeError("No algorithm classes found in source code")
                
        except Exception as e:
            raise RuntimeError(f"Failed to load algorithm from source code: {e}")
    
    def load_from_file(self, file_path: str, algorithm_name: str = None) -> Optional[Type[IAlgorithm]]:
        """Load algorithm from file by reading source code."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            return self.load_from_source(source_code, algorithm_name or "Algorithm")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load algorithm from file {file_path}: {e}")
    
    def load_from_module(self, module_path: str, algorithm_name: str = None) -> Optional[Type[IAlgorithm]]:
        """Not supported for source code loader."""
        raise NotImplementedError("SourceCodeLoader does not support loading from module paths")
    
    def validate_source_code(self, source_code: str) -> List[str]:
        """Validate source code and return list of issues."""
        issues = []
        
        try:
            # Try to parse the source code
            ast.parse(source_code)
        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")
            return issues
        
        try:
            # Try to compile
            compile(source_code, "<validation>", 'exec')
        except Exception as e:
            issues.append(f"Compilation error: {e}")
        
        # Check for algorithm class
        tree = ast.parse(source_code)
        has_algorithm_class = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if class might be an algorithm
                base_names = [base.id for base in node.bases if isinstance(base, ast.Name)]
                if any('Algorithm' in name for name in base_names):
                    has_algorithm_class = True
                    
                    # Check for required methods
                    method_names = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    required_methods = ['initialize', 'on_data']
                    
                    for required_method in required_methods:
                        if required_method not in method_names:
                            issues.append(f"Missing required method: {required_method}")
        
        if not has_algorithm_class:
            issues.append("No algorithm class found (should inherit from Algorithm or IAlgorithm)")
        
        return issues
    
    def clear_cache(self):
        """Clear the source code cache."""
        for module_name in list(self._source_cache.keys()):
            if module_name in sys.modules:
                del sys.modules[module_name]
        self._source_cache.clear()