#!/usr/bin/env python3
"""
Static analysis of potential circular import issues in the misbuffet service.
This script analyzes import patterns to identify circular dependencies.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple

class ImportAnalyzer:
    """Analyzes Python files for import patterns and circular dependencies."""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.import_graph: Dict[str, Set[str]] = {}
        self.module_files: Dict[str, Path] = {}
        
    def analyze_misbuffet_imports(self) -> Dict[str, any]:
        """Analyze imports in the misbuffet service directory."""
        misbuffet_path = self.root_path / "src" / "application" / "services" / "misbuffet"
        
        if not misbuffet_path.exists():
            return {"error": "Misbuffet directory not found"}
        
        # Scan all Python files
        python_files = list(misbuffet_path.rglob("*.py"))
        
        results = {
            "total_files": len(python_files),
            "import_patterns": {},
            "potential_issues": [],
            "key_modules": {}
        }
        
        # Analyze each file
        for file_path in python_files:
            try:
                relative_path = file_path.relative_to(self.root_path)
                module_name = str(relative_path).replace("/", ".").replace(".py", "")
                
                imports = self._extract_imports(file_path)
                self.import_graph[module_name] = set(imports)
                self.module_files[module_name] = file_path
                
                results["import_patterns"][module_name] = imports
                
                # Check for potentially problematic patterns
                if any(".." in imp for imp in imports):
                    results["potential_issues"].append({
                        "file": str(relative_path),
                        "issue": "Relative imports detected",
                        "imports": [imp for imp in imports if ".." in imp]
                    })
                    
            except Exception as e:
                results["potential_issues"].append({
                    "file": str(file_path),
                    "issue": f"Analysis error: {e}",
                    "imports": []
                })
        
        # Analyze key modules
        key_modules = [
            "src.application.services.misbuffet.common.time_utils",
            "src.application.services.misbuffet.common.__init__",
            "src.application.services.misbuffet.__init__",
            "src.application.services.misbuffet.brokers.base_broker",
            "src.application.services.misbuffet.brokers.__init__",
            "src.application.services.misbuffet.algorithm.__init__"
        ]
        
        for module in key_modules:
            if module in self.import_graph:
                results["key_modules"][module] = {
                    "imports": list(self.import_graph[module]),
                    "import_count": len(self.import_graph[module])
                }
        
        # Detect potential circular imports
        cycles = self._detect_cycles()
        if cycles:
            results["circular_imports"] = cycles
        
        return results
    
    def _extract_imports(self, file_path: Path) -> List[str]:
        """Extract import statements from a Python file."""
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        if node.level > 0:  # Relative import
                            imports.append("." * node.level + (node.module or ""))
                        else:
                            imports.append(node.module)
                        
        except Exception:
            # If parsing fails, try simple text analysis
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('import ') or line.startswith('from '):
                        if '#' in line:
                            line = line[:line.index('#')]
                        imports.append(line.strip())
                        
            except Exception:
                pass
        
        return imports
    
    def _detect_cycles(self) -> List[List[str]]:
        """Detect circular import cycles using DFS."""
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node: str, path: List[str]) -> bool:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return True
            
            if node in visited:
                return False
                
            visited.add(node)
            rec_stack.add(node)
            
            # Get dependencies for this module
            dependencies = self.import_graph.get(node, set())
            
            for dep in dependencies:
                if dep.startswith('.'):
                    # Convert relative imports to absolute
                    parts = node.split('.')
                    level = len(dep) - len(dep.lstrip('.'))
                    if level <= len(parts):
                        base_parts = parts[:-level] if level > 0 else parts
                        dep_module = '.'.join(base_parts + dep.lstrip('.').split('.')) if dep.lstrip('.') else '.'.join(base_parts)
                    else:
                        continue
                else:
                    dep_module = dep
                
                if dep_module in self.import_graph:
                    if dfs(dep_module, path + [node]):
                        return True
            
            rec_stack.remove(node)
            return False
        
        for module in self.import_graph:
            if module not in visited:
                dfs(module, [])
        
        return cycles

def main():
    """Run the import analysis."""
    print("=" * 70)
    print("MISBUFFET SERVICE IMPORT ANALYSIS")
    print("=" * 70)
    
    analyzer = ImportAnalyzer("/home/runner/work/base_infrastructure/base_infrastructure")
    results = analyzer.analyze_misbuffet_imports()
    
    if "error" in results:
        print(f"Error: {results['error']}")
        return
    
    print(f"Total Python files analyzed: {results['total_files']}")
    
    # Show key modules
    print("\nKEY MODULES:")
    print("-" * 40)
    for module, info in results.get("key_modules", {}).items():
        print(f"{module}")
        print(f"  Imports: {info['import_count']}")
        if info['imports']:
            for imp in info['imports'][:5]:  # Show first 5 imports
                print(f"    - {imp}")
            if len(info['imports']) > 5:
                print(f"    ... and {len(info['imports']) - 5} more")
        print()
    
    # Show potential issues
    if results.get("potential_issues"):
        print("POTENTIAL ISSUES:")
        print("-" * 40)
        for issue in results["potential_issues"][:10]:  # Show first 10 issues
            print(f"File: {issue['file']}")
            print(f"Issue: {issue['issue']}")
            if issue['imports']:
                print(f"Problematic imports: {issue['imports']}")
            print()
    
    # Show circular imports if detected
    if results.get("circular_imports"):
        print("CIRCULAR IMPORT CYCLES DETECTED:")
        print("-" * 40)
        for i, cycle in enumerate(results["circular_imports"], 1):
            print(f"Cycle {i}: {' → '.join(cycle)}")
        print()
    else:
        print("No obvious circular import cycles detected in static analysis.")
    
    # Recommendations
    print("RECOMMENDATIONS:")
    print("-" * 40)
    
    if results.get("potential_issues"):
        relative_imports = [issue for issue in results["potential_issues"] 
                          if "Relative imports" in issue['issue']]
        if relative_imports:
            print("1. Consider converting relative imports to absolute imports")
            print("   Relative imports can sometimes cause circular import issues")
    
    print("2. To test actual imports, run the following manually:")
    print("   python -c \"from src.application.services.misbuffet.common.time_utils import Time; print('Time import works')\"")
    print("   python -c \"import src.application.services.misbuffet; print('Main misbuffet import works')\"")
    print("   python -c \"from src.application.services.misbuffet.brokers.base_broker import BaseBroker; print('BaseBroker import works')\"")
    
    print("\n3. If imports fail, check for:")
    print("   - Missing __init__.py files")
    print("   - Incorrect relative import paths")  
    print("   - Actual circular dependencies at runtime")

if __name__ == "__main__":
    main()