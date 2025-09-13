import os
import ast
from typing import Dict, Any, List, Optional
from pathlib import Path

class FileParser:
    def __init__(self):
        pass
    
    def analyze_python_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a Python file for common issues"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                return {
                    "syntax_error": True,
                    "error": str(e),
                    "line": e.lineno,
                    "issues": ["Syntax error detected"]
                }
            
            issues = []
            warnings = []
            
            # Analyze AST nodes
            for node in ast.walk(tree):
                # Check for bare except clauses
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    issues.append(f"Bare except clause at line {node.lineno}")
                
                # Check for eval/exec usage
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ['eval', 'exec']:
                            issues.append(f"Use of {node.func.id}() at line {node.lineno} - security risk")
                
                # Check for print statements (Python 2 style)
                if isinstance(node, ast.Print):
                    warnings.append(f"Python 2 style print statement at line {node.lineno}")
            
            # Check for unused imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # Simple check for unused imports (basic implementation)
            for imp in imports:
                if imp not in content.replace(f"import {imp}", "").replace(f"from {imp}", ""):
                    warnings.append(f"Potentially unused import: {imp}")
            
            return {
                "syntax_error": False,
                "issues": issues,
                "warnings": warnings,
                "imports": imports,
                "functions": self._extract_functions(tree),
                "classes": self._extract_classes(tree)
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "issues": [f"Error analyzing file: {str(e)}"]
            }
    
    def _extract_functions(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract function information from AST"""
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": [arg.arg for arg in node.args.args],
                    "has_docstring": ast.get_docstring(node) is not None
                })
        
        return functions
    
    def _extract_classes(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract class information from AST"""
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "has_docstring": ast.get_docstring(node) is not None,
                    "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                })
        
        return classes
    
    def analyze_repository(self, repo_path: str) -> Dict[str, Any]:
        """Analyze entire repository for issues"""
        python_files = list(Path(repo_path).rglob("*.py"))
        
        analysis_results = {
            "total_files": len(python_files),
            "files_with_issues": 0,
            "total_issues": 0,
            "total_warnings": 0,
            "file_analyses": {},
            "summary": {
                "critical_issues": [],
                "warnings": [],
                "suggestions": []
            }
        }
        
        critical_issues = []
        warnings = []
        
        for py_file in python_files:
            try:
                file_analysis = self.analyze_python_file(str(py_file))
                analysis_results["file_analyses"][str(py_file.relative_to(repo_path))] = file_analysis
                
                if file_analysis.get("syntax_error"):
                    critical_issues.append(f"Syntax error in {py_file.name}")
                    analysis_results["files_with_issues"] += 1
                
                issues = file_analysis.get("issues", [])
                warnings_list = file_analysis.get("warnings", [])
                
                analysis_results["total_issues"] += len(issues)
                analysis_results["total_warnings"] += len(warnings_list)
                
                if issues:
                    analysis_results["files_with_issues"] += 1
                    critical_issues.extend([f"{py_file.name}: {issue}" for issue in issues])
                
                warnings.extend([f"{py_file.name}: {warning}" for warning in warnings_list])
                
            except Exception as e:
                critical_issues.append(f"Error analyzing {py_file.name}: {str(e)}")
        
        analysis_results["summary"]["critical_issues"] = critical_issues
        analysis_results["summary"]["warnings"] = warnings
        
        # Generate suggestions
        suggestions = []
        if analysis_results["total_issues"] > 0:
            suggestions.append("Review and fix critical issues before deployment")
        if analysis_results["total_warnings"] > 0:
            suggestions.append("Consider addressing warnings for better code quality")
        if analysis_results["files_with_issues"] == 0:
            suggestions.append("Code appears to be in good condition")
        
        analysis_results["summary"]["suggestions"] = suggestions
        
        return analysis_results