#!/usr/bin/env python3
"""
Simple factor infrastructure validation script.
Checks basic import structure and syntax of the newly created files.
"""

import ast
import os
from pathlib import Path

class SimpleFactorValidator:
    def __init__(self):
        self.results = {
            'syntax_valid': [],
            'syntax_invalid': [],
            'import_issues': [],
            'total_files': 0
        }
        self.base_path = Path("/home/runner/work/base_infrastructure/base_infrastructure")
    
    def check_python_syntax(self, file_path):
        """Check if a Python file has valid syntax."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to parse the AST
            ast.parse(content)
            self.results['syntax_valid'].append(str(file_path))
            return True
        except SyntaxError as e:
            self.results['syntax_invalid'].append({
                'file': str(file_path),
                'error': f"Line {e.lineno}: {e.msg}"
            })
            return False
        except Exception as e:
            self.results['syntax_invalid'].append({
                'file': str(file_path),
                'error': str(e)
            })
            return False
    
    def check_imports_in_file(self, file_path):
        """Check imports in a Python file and identify potential issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(f"{node.module}.{node.names[0].name}")
            
            # Check for common import issues
            suspicious_imports = []
            for imp in imports:
                if 'src.domain.entities.factor' in imp and 'factor.factor' not in imp:
                    # Check if the imported module might have naming issues
                    pass
                if imp.count('.') > 6:  # Very deep imports might indicate issues
                    suspicious_imports.append(imp)
            
            if suspicious_imports:
                self.results['import_issues'].append({
                    'file': str(file_path),
                    'issues': suspicious_imports
                })
                
        except Exception as e:
            self.results['import_issues'].append({
                'file': str(file_path),
                'error': f"Could not analyze imports: {str(e)}"
            })
    
    def validate_directory(self, directory_path):
        """Validate all Python files in a directory."""
        directory = Path(directory_path)
        if not directory.exists():
            print(f"Directory does not exist: {directory}")
            return
        
        python_files = list(directory.rglob("*.py"))
        self.results['total_files'] += len(python_files)
        
        print(f"Checking {len(python_files)} files in {directory}")
        
        for py_file in python_files:
            if py_file.name == '__init__.py':
                continue  # Skip __init__ files
                
            # Check syntax
            self.check_python_syntax(py_file)
            
            # Check imports
            self.check_imports_in_file(py_file)
    
    def run_validation(self):
        """Run complete validation on factor infrastructure."""
        print("=" * 80)
        print("FACTOR INFRASTRUCTURE SYNTAX AND IMPORT VALIDATION")
        print("=" * 80)
        
        # Check all factor-related directories
        factor_dirs = [
            "src/infrastructure/repositories/mappers/factor",
            "src/domain/ports/factor",
            "src/infrastructure/repositories/local_repo/factor/finance/financial_assets",
            "src/infrastructure/repositories/ibkr_repo/factor/finance/financial_assets"
        ]
        
        for directory in factor_dirs:
            full_path = self.base_path / directory
            print(f"\nValidating: {directory}")
            self.validate_directory(full_path)
        
        # Also check the repository factory
        factory_file = self.base_path / "src/infrastructure/repositories/repository_factory.py"
        if factory_file.exists():
            print(f"\nValidating repository factory: {factory_file}")
            self.check_python_syntax(factory_file)
            self.check_imports_in_file(factory_file)
            self.results['total_files'] += 1
        
        self.print_results()
    
    def print_results(self):
        """Print validation results."""
        print("\n" + "=" * 80)
        print("VALIDATION RESULTS")
        print("=" * 80)
        
        print(f"Total files checked: {self.results['total_files']}")
        print(f"Files with valid syntax: {len(self.results['syntax_valid'])}")
        print(f"Files with syntax errors: {len(self.results['syntax_invalid'])}")
        print(f"Files with import issues: {len(self.results['import_issues'])}")
        
        if self.results['syntax_invalid']:
            print("\n" + "-" * 40)
            print("SYNTAX ERRORS:")
            for error in self.results['syntax_invalid']:
                print(f"  ❌ {error['file']}")
                print(f"     Error: {error['error']}")
        
        if self.results['import_issues']:
            print("\n" + "-" * 40)
            print("IMPORT ISSUES:")
            for issue in self.results['import_issues']:
                print(f"  ⚠️  {issue['file']}")
                if 'issues' in issue:
                    for imp in issue['issues']:
                        print(f"     Suspicious import: {imp}")
                if 'error' in issue:
                    print(f"     Error: {issue['error']}")
        
        if not self.results['syntax_invalid'] and not self.results['import_issues']:
            print("\n🎉 ALL FILES PASSED BASIC VALIDATION!")
            print("✅ No syntax errors found")
            print("✅ No obvious import issues detected")
        else:
            print(f"\n⚠️  Found {len(self.results['syntax_invalid'])} syntax errors and {len(self.results['import_issues'])} import issues")
        
        # Summary statistics
        success_rate = (len(self.results['syntax_valid']) / max(1, self.results['total_files'])) * 100
        print(f"\nSuccess rate: {success_rate:.1f}%")

if __name__ == "__main__":
    validator = SimpleFactorValidator()
    validator.run_validation()