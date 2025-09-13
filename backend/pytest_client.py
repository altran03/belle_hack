import os
import subprocess
import json
import tempfile
import ast
import re
from typing import Dict, Any, List, Optional
import asyncio
from pathlib import Path
import time

class PytestClient:
    def __init__(self):
        self.mock_mode = os.getenv("PYTEST_MOCK", "0") == "1"
    
    async def run_tests(self, repo_path: str) -> Dict[str, Any]:
        """
        Run pytest tests on the repository
        Returns test results with diagnostics
        """
        if self.mock_mode:
            return await self._mock_test_results(repo_path)
        
        try:
            # Try to run pytest
            pytest_result = await self._run_pytest(repo_path)
            if pytest_result:
                return pytest_result
            
            # If pytest fails, fall back to static analysis
            print("Pytest failed, falling back to static analysis")
            return await self._run_static_analysis(repo_path)
            
        except Exception as e:
            print(f"Pytest execution failed: {e}")
            return await self._run_static_analysis(repo_path)
    
    async def run_tests_with_patch(self, repo_path: str, patch_content: str) -> Dict[str, Any]:
        """
        Apply patch and run tests
        """
        # Create a temporary copy of the repo
        temp_repo = tempfile.mkdtemp(prefix="pytest_patch_")
        
        try:
            # Copy repo to temp location
            import shutil
            shutil.copytree(repo_path, temp_repo, dirs_exist_ok=True)
            
            # Apply patch
            patch_file = os.path.join(temp_repo, "patch.diff")
            with open(patch_file, "w") as f:
                f.write(patch_content)
            
            # Apply patch using git
            try:
                subprocess.run(["git", "apply", patch_file], 
                             cwd=temp_repo, check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                return {
                    "passed": False,
                    "total_tests": 0,
                    "failed_tests": 1,
                    "diagnostics": [f"Failed to apply patch: {e.stderr.decode()}"],
                    "error_details": str(e),
                    "execution_time": 0.0
                }
            
            # Run tests on patched code
            return await self.run_tests(temp_repo)
            
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(temp_repo, ignore_errors=True)
    
    async def _mock_test_results(self, repo_path: str) -> Dict[str, Any]:
        """
        Mock pytest results for development/testing
        Analyzes the repository and returns simulated test results
        """
        await asyncio.sleep(1)  # Simulate test execution time
        
        # Analyze the repository for common issues
        diagnostics = []
        bugs_detected = []
        
        # Check for Python files
        python_files = list(Path(repo_path).rglob("*.py"))
        
        if not python_files:
            return {
                "passed": True,
                "total_tests": 0,
                "failed_tests": 0,
                "diagnostics": ["No Python files found"],
                "error_details": None,
                "execution_time": 1.0
            }
        
        # Analyze each Python file for common issues
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for common Python issues
                if "import " in content and "from " in content:
                    # Check for unused imports
                    lines = content.split('\n')
                    imports = [line for line in lines if line.strip().startswith(('import ', 'from '))]
                    
                    for import_line in imports:
                        if 'import' in import_line:
                            module_name = import_line.split('import')[1].strip().split()[0]
                            if module_name not in content.replace(import_line, ''):
                                diagnostics.append(f"Unused import '{module_name}' in {py_file.name}")
                
                # Check for syntax issues
                if "print(" in content and "print " in content:
                    diagnostics.append(f"Mixed print syntax in {py_file.name}")
                
                # Check for potential bugs
                if "except:" in content:
                    diagnostics.append(f"Bare except clause in {py_file.name}")
                    bugs_detected.append("Bare except clause - should specify exception type")
                
                if "eval(" in content:
                    diagnostics.append(f"Use of eval() in {py_file.name}")
                    bugs_detected.append("Use of eval() - security risk")
                
                if "exec(" in content:
                    diagnostics.append(f"Use of exec() in {py_file.name}")
                    bugs_detected.append("Use of exec() - security risk")
                
                # Check for missing docstrings in functions
                lines = content.split('\n')
                in_function = False
                function_name = None
                
                for i, line in enumerate(lines):
                    if line.strip().startswith('def '):
                        in_function = True
                        function_name = line.strip().split('(')[0].replace('def ', '')
                        # Check if next non-empty line is a docstring
                        next_line_idx = i + 1
                        while next_line_idx < len(lines) and not lines[next_line_idx].strip():
                            next_line_idx += 1
                        
                        if (next_line_idx < len(lines) and 
                            not lines[next_line_idx].strip().startswith('"""') and
                            not lines[next_line_idx].strip().startswith("'''")):
                            diagnostics.append(f"Function '{function_name}' in {py_file.name} missing docstring")
                
            except Exception as e:
                diagnostics.append(f"Error analyzing {py_file.name}: {str(e)}")
        
        # Simulate test results
        total_tests = len(python_files) * 3  # Assume 3 tests per file
        failed_tests = len(bugs_detected) + len([d for d in diagnostics if "error" in d.lower()])
        
        return {
            "passed": failed_tests == 0,
            "total_tests": total_tests,
            "failed_tests": failed_tests,
            "diagnostics": diagnostics,
            "error_details": None if failed_tests == 0 else f"Found {failed_tests} issues",
            "execution_time": 1.5 + len(python_files) * 0.1
        }
    
    async def _run_pytest(self, repo_path: str) -> Optional[Dict[str, Any]]:
        """
        Run pytest on the repository
        """
        try:
            print(f"Running pytest on {repo_path}")
            
            # Check if pytest is available
            try:
                subprocess.run(["pytest", "--version"], 
                             capture_output=True, check=True, timeout=10)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                print("Pytest not available")
                return None
            
            # Look for existing test files
            test_files = []
            for root, dirs, files in os.walk(repo_path):
                for file in files:
                    if (file.startswith('test_') or file.endswith('_test.py') or 
                        'test' in file.lower() and file.endswith('.py')):
                        test_files.append(os.path.join(root, file))
            
            # If no test files found, try to run pytest on the main files to check for syntax errors
            if not test_files:
                print("No test files found, running pytest on Python files for syntax checking")
                python_files = list(Path(repo_path).rglob("*.py"))
                if not python_files:
                    print("No Python files found")
                    return None
                
                # Run pytest with --collect-only to check for syntax errors
                start_time = time.time()
                result = subprocess.run(
                    ["pytest", "--collect-only", "-q", str(repo_path)],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                execution_time = time.time() - start_time
                
                # Parse the output
                diagnostics = []
                total_tests = 0
                failed_tests = 0
                
                if result.returncode == 0:
                    # Success - count collected tests
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'test session starts' in line.lower():
                            continue
                        elif 'collected' in line.lower() and 'item' in line.lower():
                            # Extract number of collected tests
                            import re
                            numbers = re.findall(r'\d+', line)
                            if numbers:
                                total_tests = int(numbers[0])
                        elif 'error' in line.lower() or 'failed' in line.lower():
                            diagnostics.append(line.strip())
                            failed_tests += 1
                    
                    return {
                        "passed": failed_tests == 0,
                        "total_tests": max(total_tests, 1),
                        "failed_tests": failed_tests,
                        "diagnostics": diagnostics if diagnostics else ["Pytest syntax check passed"],
                        "error_details": None if failed_tests == 0 else "Syntax errors found",
                        "execution_time": execution_time,
                        "test_method": "pytest_syntax_check"
                    }
                else:
                    # Pytest found issues
                    diagnostics = result.stderr.split('\n') if result.stderr else result.stdout.split('\n')
                    diagnostics = [d.strip() for d in diagnostics if d.strip()]
                    
                    return {
                        "passed": False,
                        "total_tests": 1,
                        "failed_tests": 1,
                        "diagnostics": diagnostics[:10],  # Limit to first 10 errors
                        "error_details": "Pytest found syntax or import errors",
                        "execution_time": execution_time,
                        "test_method": "pytest_syntax_check"
                    }
            
            else:
                # Run actual tests
                print(f"Found {len(test_files)} test files, running pytest")
                start_time = time.time()
                
                result = subprocess.run(
                    ["pytest", "-v", "--tb=short", str(repo_path)],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minute timeout for actual tests
                )
                execution_time = time.time() - start_time
                
                # Parse pytest output
                return self._parse_pytest_output(result, execution_time)
                
        except subprocess.TimeoutExpired:
            print("Pytest timed out")
            return {
                "passed": False,
                "total_tests": 0,
                "failed_tests": 1,
                "diagnostics": ["Pytest timed out after 2 minutes"],
                "error_details": "Pytest execution timeout",
                "execution_time": 120.0,
                "test_method": "pytest_timeout"
            }
        except Exception as e:
            print(f"Pytest failed: {e}")
            return None
    
    def _parse_pytest_output(self, result: subprocess.CompletedProcess, execution_time: float) -> Dict[str, Any]:
        """Parse pytest output into our expected format"""
        try:
            diagnostics = []
            total_tests = 0
            failed_tests = 0
            
            # Parse stdout for test results
            lines = result.stdout.split('\n')
            for line in lines:
                if '::' in line and ('PASSED' in line or 'FAILED' in line or 'ERROR' in line):
                    total_tests += 1
                    if 'FAILED' in line or 'ERROR' in line:
                        failed_tests += 1
                        diagnostics.append(line.strip())
                elif 'failed' in line.lower() and 'passed' in line.lower():
                    # Summary line like "1 failed, 2 passed in 0.5s"
                    import re
                    numbers = re.findall(r'\d+', line)
                    if len(numbers) >= 2:
                        failed_tests = int(numbers[0])
                        passed_tests = int(numbers[1])
                        total_tests = failed_tests + passed_tests
            
            # If no tests found in stdout, check stderr
            if total_tests == 0 and result.stderr:
                stderr_lines = result.stderr.split('\n')
                for line in stderr_lines:
                    if 'error' in line.lower() or 'failed' in line.lower():
                        diagnostics.append(line.strip())
                        failed_tests += 1
                        total_tests += 1
            
            # If still no tests found, check return code
            if total_tests == 0:
                if result.returncode == 0:
                    return {
                        "passed": True,
                        "total_tests": 1,
                        "failed_tests": 0,
                        "diagnostics": ["Pytest completed successfully"],
                        "error_details": None,
                        "execution_time": execution_time,
                        "test_method": "pytest"
                    }
                else:
                    # Try to extract more information from stderr
                    error_details = result.stderr or result.stdout or "Unknown pytest error"
                    diagnostics = []
                    if result.stderr:
                        diagnostics.extend([line.strip() for line in result.stderr.split('\n') if line.strip()][:5])
                    if result.stdout:
                        diagnostics.extend([line.strip() for line in result.stdout.split('\n') if line.strip()][:5])
                    
                    return {
                        "passed": False,
                        "total_tests": 1,
                        "failed_tests": 1,
                        "diagnostics": diagnostics if diagnostics else ["Pytest failed to run tests"],
                        "error_details": error_details,
                        "execution_time": execution_time,
                        "test_method": "pytest"
                    }
            
            return {
                "passed": failed_tests == 0,
                "total_tests": total_tests,
                "failed_tests": failed_tests,
                "diagnostics": diagnostics[:10],  # Limit to first 10 failures
                "error_details": None if failed_tests == 0 else f"Pytest found {failed_tests} test failures",
                "execution_time": execution_time,
                "test_method": "pytest"
            }
            
        except Exception as e:
            return {
                "passed": False,
                "total_tests": 0,
                "failed_tests": 1,
                "diagnostics": [f"Error parsing pytest output: {str(e)}"],
                "error_details": str(e),
                "execution_time": execution_time,
                "test_method": "pytest_parse_error"
            }

    async def _run_static_analysis(self, repo_path: str) -> Dict[str, Any]:
        """Fallback static analysis when pytest fails"""
        try:
            import ast
            import re
            
            diagnostics = []
            total_tests = 0
            failed_tests = 0
            
            # Walk through Python files in the repository
            for root, dirs, files in os.walk(repo_path):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Parse the AST
                            try:
                                tree = ast.parse(content)
                            except SyntaxError as e:
                                diagnostics.append(f"Syntax error in {file}: {e}")
                                failed_tests += 1
                                total_tests += 1
                                continue
                            
                            # Check for various issues
                            issues = self._analyze_ast_for_issues(tree, file)
                            diagnostics.extend(issues)
                            failed_tests += len(issues)
                            total_tests += 1
                            
                            # Also check for patterns in the raw content
                            pattern_issues = self._analyze_content_patterns(content, file)
                            diagnostics.extend(pattern_issues)
                            failed_tests += len(pattern_issues)
                            
                        except Exception as e:
                            diagnostics.append(f"Error analyzing {file}: {e}")
                            failed_tests += 1
                            total_tests += 1
            
            return {
                "passed": failed_tests == 0,
                "total_tests": max(total_tests, 1),
                "failed_tests": failed_tests,
                "diagnostics": diagnostics,
                "error_details": None if failed_tests == 0 else f"Static analysis found {failed_tests} issues",
                "execution_time": 0.0
            }
            
        except Exception as e:
            return {
                "passed": False,
                "total_tests": 0,
                "failed_tests": 1,
                "diagnostics": [f"Static analysis failed: {str(e)}"],
                "error_details": str(e),
                "execution_time": 0.0
            }
    
    def _analyze_ast_for_issues(self, tree: ast.AST, filename: str) -> List[str]:
        """Analyze AST for common issues"""
        issues = []
        
        class IssueVisitor(ast.NodeVisitor):
            def visit_Import(self, node):
                # Check for unused imports (simplified check)
                for alias in node.names:
                    if alias.name == 'datetime' and 'datetime' not in str(tree):
                        issues.append(f"Unused import 'datetime' in {filename}")
                self.generic_visit(node)
            
            def visit_ExceptHandler(self, node):
                if node.type is None:
                    issues.append(f"Bare except clause in {filename} (line {node.lineno})")
                self.generic_visit(node)
            
            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    if node.func.id == 'eval':
                        issues.append(f"Use of eval() detected in {filename} (line {node.lineno}) - security risk")
                    elif node.func.id == 'exec':
                        issues.append(f"Use of exec() detected in {filename} (line {node.lineno}) - security risk")
                self.generic_visit(node)
            
            def visit_FunctionDef(self, node):
                # Check for missing docstrings
                if not ast.get_docstring(node) and not node.name.startswith('_'):
                    issues.append(f"Function '{node.name}' in {filename} missing docstring")
                
                # Check for missing type hints
                if node.returns is None and not node.name.startswith('_'):
                    issues.append(f"Function '{node.name}' in {filename} missing return type hint")
                
                self.generic_visit(node)
        
        visitor = IssueVisitor()
        visitor.visit(tree)
        return issues
    
    def _analyze_content_patterns(self, content: str, filename: str) -> List[str]:
        """Analyze content for patterns that indicate issues"""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for hardcoded paths
            if '/tmp/' in line or '/var/' in line:
                issues.append(f"Hardcoded path detected in {filename} (line {i}): {line.strip()}")
            
            # Check for Python 2 style print statements
            if re.search(r'\bprint\s+[^(]', line):
                issues.append(f"Python 2 style print statement in {filename} (line {i}): {line.strip()}")
            
            # Check for global variables
            if line.strip().startswith('global '):
                issues.append(f"Global variable usage in {filename} (line {i}): {line.strip()}")
            
            # Check for resource leaks (open without close)
            if 'open(' in line and 'with ' not in line and 'close()' not in content:
                issues.append(f"Potential resource leak in {filename} (line {i}): file opened without proper cleanup")
        
        return issues
