"""
Compilers for algorithm source code.
"""

import ast
import py_compile
import tempfile
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..common.enums import Language


@dataclass
class CompilerError:
    """
    Represents a compilation error.
    """
    line: int
    column: int
    message: str
    severity: str  # 'error', 'warning', 'info'
    file_path: str = ""
    
    def __str__(self) -> str:
        location = f"{self.file_path}:{self.line}:{self.column}" if self.file_path else f"{self.line}:{self.column}"
        return f"{self.severity.upper()}: {location}: {self.message}"


@dataclass
class CompilerResults:
    """
    Results of a compilation operation.
    """
    success: bool
    errors: List[CompilerError]
    warnings: List[CompilerError]
    output_file: Optional[str] = None
    compilation_time: float = 0.0
    compiler_output: str = ""
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0
    
    def get_all_issues(self) -> List[CompilerError]:
        """Get all errors and warnings combined."""
        return self.errors + self.warnings
    
    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return (f"CompilerResults({status}, errors={len(self.errors)}, "
                f"warnings={len(self.warnings)}, time={self.compilation_time:.3f}s)")


class PythonCompiler:
    """
    Compiler for Python algorithm source code.
    """
    
    def __init__(self):
        self.optimization_level = 2  # Python optimization level
        self.check_syntax = True
        self.check_style = False  # Optional style checking
        self.lint_enabled = False  # Optional linting
    
    def compile(self, source_path: str, output_path: str = None) -> CompilerResults:
        """
        Compile Python source code.
        
        Args:
            source_path: Path to source code file
            output_path: Optional output path for compiled bytecode
            
        Returns:
            Compilation results
        """
        start_time = datetime.now()
        errors = []
        warnings = []
        
        source_path_obj = Path(source_path)
        
        if not source_path_obj.exists():
            errors.append(CompilerError(
                line=0, column=0,
                message=f"Source file not found: {source_path}",
                severity="error",
                file_path=source_path
            ))
            return CompilerResults(
                success=False,
                errors=errors,
                warnings=warnings,
                compilation_time=(datetime.now() - start_time).total_seconds()
            )
        
        try:
            # Read source code
            with open(source_path_obj, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Syntax checking
            if self.check_syntax:
                syntax_errors = self._check_syntax(source_code, str(source_path_obj))
                errors.extend(syntax_errors)
            
            # If no syntax errors, proceed with compilation
            if not errors:
                output_file = None
                
                if output_path:
                    # Compile to bytecode
                    try:
                        py_compile.compile(
                            str(source_path_obj),
                            output_path,
                            optimize=self.optimization_level
                        )
                        output_file = output_path
                    except py_compile.PyCompileError as e:
                        errors.append(CompilerError(
                            line=0, column=0,
                            message=f"Compilation failed: {e}",
                            severity="error",
                            file_path=source_path
                        ))
                
                # Style checking (optional)
                if self.check_style and not errors:
                    style_warnings = self._check_style(source_code, str(source_path_obj))
                    warnings.extend(style_warnings)
                
                # Linting (optional)
                if self.lint_enabled and not errors:
                    lint_issues = self._run_linter(str(source_path_obj))
                    for issue in lint_issues:
                        if issue.severity == "error":
                            errors.append(issue)
                        else:
                            warnings.append(issue)
                
                compilation_time = (datetime.now() - start_time).total_seconds()
                
                return CompilerResults(
                    success=len(errors) == 0,
                    errors=errors,
                    warnings=warnings,
                    output_file=output_file,
                    compilation_time=compilation_time
                )
            
        except Exception as e:
            errors.append(CompilerError(
                line=0, column=0,
                message=f"Unexpected compilation error: {e}",
                severity="error",
                file_path=source_path
            ))
        
        compilation_time = (datetime.now() - start_time).total_seconds()
        
        return CompilerResults(
            success=False,
            errors=errors,
            warnings=warnings,
            compilation_time=compilation_time
        )
    
    def compile_source(self, source_code: str, file_name: str = "<string>") -> CompilerResults:
        """
        Compile Python source code from string.
        
        Args:
            source_code: Python source code
            file_name: Name for the source (for error reporting)
            
        Returns:
            Compilation results
        """
        start_time = datetime.now()
        errors = []
        warnings = []
        
        try:
            # Syntax checking
            if self.check_syntax:
                syntax_errors = self._check_syntax(source_code, file_name)
                errors.extend(syntax_errors)
            
            # Try to compile
            if not errors:
                try:
                    compile(source_code, file_name, 'exec', optimize=self.optimization_level)
                except SyntaxError as e:
                    errors.append(CompilerError(
                        line=e.lineno or 0,
                        column=e.offset or 0,
                        message=e.msg or "Syntax error",
                        severity="error",
                        file_path=file_name
                    ))
                except Exception as e:
                    errors.append(CompilerError(
                        line=0, column=0,
                        message=f"Compilation error: {e}",
                        severity="error",
                        file_path=file_name
                    ))
            
            # Style checking (optional)
            if self.check_style and not errors:
                style_warnings = self._check_style(source_code, file_name)
                warnings.extend(style_warnings)
            
            compilation_time = (datetime.now() - start_time).total_seconds()
            
            return CompilerResults(
                success=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                compilation_time=compilation_time
            )
            
        except Exception as e:
            errors.append(CompilerError(
                line=0, column=0,
                message=f"Unexpected compilation error: {e}",
                severity="error",
                file_path=file_name
            ))
            
            compilation_time = (datetime.now() - start_time).total_seconds()
            
            return CompilerResults(
                success=False,
                errors=errors,
                warnings=warnings,
                compilation_time=compilation_time
            )
    
    def _check_syntax(self, source_code: str, file_name: str) -> List[CompilerError]:
        """Check syntax of Python source code."""
        errors = []
        
        try:
            ast.parse(source_code, filename=file_name)
        except SyntaxError as e:
            errors.append(CompilerError(
                line=e.lineno or 0,
                column=e.offset or 0,
                message=e.msg or "Syntax error",
                severity="error",
                file_path=file_name
            ))
        except Exception as e:
            errors.append(CompilerError(
                line=0, column=0,
                message=f"Parse error: {e}",
                severity="error",
                file_path=file_name
            ))
        
        return errors
    
    def _check_style(self, source_code: str, file_name: str) -> List[CompilerError]:
        """Check code style (simplified)."""
        warnings = []
        
        try:
            tree = ast.parse(source_code, filename=file_name)
            
            # Simple style checks
            for node in ast.walk(tree):
                # Check for long lines (simplified)
                if isinstance(node, ast.stmt) and hasattr(node, 'lineno'):
                    lines = source_code.split('\n')
                    if node.lineno <= len(lines):
                        line = lines[node.lineno - 1]
                        if len(line) > 100:  # PEP 8 recommends 79, but 100 is common
                            warnings.append(CompilerError(
                                line=node.lineno,
                                column=0,
                                message=f"Line too long ({len(line)} characters)",
                                severity="warning",
                                file_path=file_name
                            ))
                
                # Check for unused imports (very basic)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        # This is a very basic check - a real implementation would be more sophisticated
                        if alias.name not in source_code.replace(f"import {alias.name}", ""):
                            warnings.append(CompilerError(
                                line=node.lineno or 0,
                                column=0,
                                message=f"Potentially unused import: {alias.name}",
                                severity="warning",
                                file_path=file_name
                            ))
        
        except Exception as e:
            # Style checking errors shouldn't fail compilation
            pass
        
        return warnings
    
    def _run_linter(self, file_path: str) -> List[CompilerError]:
        """Run external linter (like pylint or flake8)."""
        issues = []
        
        try:
            # Try to run flake8 if available
            result = subprocess.run(
                [sys.executable, '-m', 'flake8', file_path, '--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and not result.stdout.strip():
                # No issues found
                return issues
            
            # Parse flake8 output
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            line_num = int(parts[1])
                            col_num = int(parts[2])
                            message = parts[3].strip()
                            
                            # Determine severity based on error code
                            severity = "warning"
                            if any(message.startswith(code) for code in ['E', 'F']):
                                severity = "error"
                            
                            issues.append(CompilerError(
                                line=line_num,
                                column=col_num,
                                message=message,
                                severity=severity,
                                file_path=file_path
                            ))
                    except (ValueError, IndexError):
                        continue
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            # Linter not available or failed - don't fail compilation
            pass
        except Exception as e:
            # Add a warning about linter failure
            issues.append(CompilerError(
                line=0, column=0,
                message=f"Linter failed: {e}",
                severity="warning",
                file_path=file_path
            ))
        
        return issues
    
    def validate_algorithm_code(self, source_code: str) -> List[CompilerError]:
        """
        Validate algorithm-specific requirements.
        
        Args:
            source_code: Python source code to validate
            
        Returns:
            List of validation errors/warnings
        """
        issues = []
        
        try:
            tree = ast.parse(source_code)
            
            # Check for algorithm class
            has_algorithm_class = False
            algorithm_classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if class might be an algorithm
                    base_names = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_names.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            base_names.append(base.attr)
                    
                    if any('Algorithm' in name for name in base_names):
                        has_algorithm_class = True
                        algorithm_classes.append(node)
            
            if not has_algorithm_class:
                issues.append(CompilerError(
                    line=0, column=0,
                    message="No algorithm class found (should inherit from Algorithm or IAlgorithm)",
                    severity="error"
                ))
            
            # Validate algorithm classes
            for class_node in algorithm_classes:
                # Check for required methods
                method_names = [n.name for n in class_node.body if isinstance(n, ast.FunctionDef)]
                required_methods = ['initialize', 'on_data']
                
                for required_method in required_methods:
                    if required_method not in method_names:
                        issues.append(CompilerError(
                            line=class_node.lineno or 0,
                            column=0,
                            message=f"Algorithm class '{class_node.name}' missing required method: {required_method}",
                            severity="error"
                        ))
                
                # Check for common methods
                recommended_methods = ['on_order_event', 'on_end_of_algorithm']
                for recommended_method in recommended_methods:
                    if recommended_method not in method_names:
                        issues.append(CompilerError(
                            line=class_node.lineno or 0,
                            column=0,
                            message=f"Algorithm class '{class_node.name}' missing recommended method: {recommended_method}",
                            severity="warning"
                        ))
            
            # Check for potential issues
            self._check_algorithm_best_practices(tree, issues)
            
        except SyntaxError as e:
            issues.append(CompilerError(
                line=e.lineno or 0,
                column=e.offset or 0,
                message=f"Syntax error: {e.msg}",
                severity="error"
            ))
        except Exception as e:
            issues.append(CompilerError(
                line=0, column=0,
                message=f"Validation error: {e}",
                severity="error"
            ))
        
        return issues
    
    def _check_algorithm_best_practices(self, tree: ast.AST, issues: List[CompilerError]):
        """Check for algorithm best practices."""
        
        # Check for infinite loops
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                # Check for while True without break
                if (isinstance(node.test, ast.Constant) and node.test.value is True):
                    has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                    if not has_break:
                        issues.append(CompilerError(
                            line=node.lineno or 0,
                            column=0,
                            message="Potential infinite loop detected",
                            severity="warning"
                        ))
            
            # Check for time.sleep in algorithm methods
            if isinstance(node, ast.Call):
                if (isinstance(node.func, ast.Attribute) and 
                    isinstance(node.func.value, ast.Name) and
                    node.func.value.id == 'time' and
                    node.func.attr == 'sleep'):
                    issues.append(CompilerError(
                        line=node.lineno or 0,
                        column=0,
                        message="Avoid using time.sleep in algorithms - use scheduling instead",
                        severity="warning"
                    ))
    
    def get_compiler_info(self) -> Dict[str, Any]:
        """Get information about the compiler."""
        return {
            'language': Language.PYTHON.value,
            'python_version': sys.version,
            'optimization_level': self.optimization_level,
            'syntax_checking': self.check_syntax,
            'style_checking': self.check_style,
            'linting_enabled': self.lint_enabled
        }
    
    def set_options(self, **options):
        """Set compiler options."""
        if 'optimization_level' in options:
            self.optimization_level = options['optimization_level']
        if 'check_syntax' in options:
            self.check_syntax = options['check_syntax']
        if 'check_style' in options:
            self.check_style = options['check_style']
        if 'lint_enabled' in options:
            self.lint_enabled = options['lint_enabled']


class BatchCompiler:
    """
    Compiler for multiple algorithm files.
    """
    
    def __init__(self, compiler: PythonCompiler):
        self.compiler = compiler
    
    def compile_directory(self, directory_path: str, output_directory: str = None,
                         file_pattern: str = "*.py") -> Dict[str, CompilerResults]:
        """
        Compile all files in a directory.
        
        Args:
            directory_path: Directory containing source files
            output_directory: Optional output directory
            file_pattern: File pattern to match
            
        Returns:
            Dictionary mapping file paths to compilation results
        """
        results = {}
        directory_path_obj = Path(directory_path)
        
        if not directory_path_obj.exists() or not directory_path_obj.is_dir():
            return results
        
        source_files = list(directory_path_obj.glob(file_pattern))
        
        for source_file in source_files:
            try:
                output_file = None
                if output_directory:
                    output_dir = Path(output_directory)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_file = str(output_dir / f"{source_file.stem}.pyc")
                
                result = self.compiler.compile(str(source_file), output_file)
                results[str(source_file)] = result
                
            except Exception as e:
                # Create error result for failed compilation
                results[str(source_file)] = CompilerResults(
                    success=False,
                    errors=[CompilerError(
                        line=0, column=0,
                        message=f"Failed to compile: {e}",
                        severity="error",
                        file_path=str(source_file)
                    )],
                    warnings=[]
                )
        
        return results
    
    def get_summary(self, results: Dict[str, CompilerResults]) -> Dict[str, Any]:
        """Get summary of compilation results."""
        total_files = len(results)
        successful_files = sum(1 for result in results.values() if result.success)
        failed_files = total_files - successful_files
        
        total_errors = sum(len(result.errors) for result in results.values())
        total_warnings = sum(len(result.warnings) for result in results.values())
        
        avg_compilation_time = (
            sum(result.compilation_time for result in results.values()) / total_files
            if total_files > 0 else 0
        )
        
        return {
            'total_files': total_files,
            'successful_files': successful_files,
            'failed_files': failed_files,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'average_compilation_time': avg_compilation_time,
            'success_rate': (successful_files / total_files * 100) if total_files > 0 else 0
        }