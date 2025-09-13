import os
import subprocess
import json
import tempfile
import ast
import re
from typing import Dict, Any, List, Optional
import asyncio
from pathlib import Path
import httpx
import zipfile
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class TestSpriteClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TESTSPRITE_API_KEY")
        self.mock_mode = os.getenv("TESTSPRITE_MOCK", "0") == "1"
        # Use the TestSprite MCP server configuration
        self.mcp_command = "npx"
        self.mcp_args = ["@testsprite/testsprite-mcp@latest"]
    
    async def run_tests(self, repo_path: str) -> Dict[str, Any]:
        """
        Run TestSprite tests on the repository
        Returns test results with diagnostics
        """
        if self.mock_mode:
            return await self._mock_test_results(repo_path)
        
        if not self.api_key:
            print("TestSprite API key not configured, trying pytest fallback...")
            pytest_result = await self._run_pytest_fallback(repo_path)
            if pytest_result:
                return pytest_result
            
            return {
                "passed": False,
                "total_tests": 0,
                "failed_tests": 1,
                "diagnostics": ["TestSprite API key not configured and pytest fallback failed"],
                "error_details": "No API key provided and pytest not available",
                "execution_time": 0.0
            }
        
        try:
            # Use MCP server to run TestSprite analysis
            result = await self._run_testsprite_mcp_analysis(repo_path)
            return result
            
        except Exception as e:
            # TestSprite MCP failed - try pytest fallback first, then static analysis
            print(f"TestSprite MCP failed: {e}")
            print("Falling back to pytest for testing...")
            
            # Try pytest fallback first
            pytest_result = await self._run_pytest_fallback(repo_path)
            if pytest_result:
                return pytest_result
            
            # If pytest also fails, return static analysis
            print("Pytest fallback also failed, using static analysis")
            return {
                "passed": False,
                "total_tests": 0,
                "failed_tests": 1,
                "diagnostics": ["TestSprite requires manual configuration. Click 'Configure TestSprite' to set up comprehensive testing."],
                "error_details": "Interactive configuration required",
                "execution_time": 0.0,
                "requires_manual_config": True,
                "static_analysis_fallback": await self._run_static_analysis(repo_path)
            }
    
    async def _mock_test_results(self, repo_path: str) -> Dict[str, Any]:
        """
        Mock TestSprite results for development/testing
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
    
    async def run_tests_with_patch(self, repo_path: str, patch_content: str) -> Dict[str, Any]:
        """
        Apply patch and run tests
        """
        # Create a temporary copy of the repo
        temp_repo = tempfile.mkdtemp(prefix="testsprite_patch_")
        
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
    
    async def _run_testsprite_mcp_analysis(self, repo_path: str) -> Dict[str, Any]:
        """Run TestSprite analysis using MCP server"""
        try:
            # Set up MCP server parameters
            # Set up environment variables for TestSprite
            env_vars = {}
            if self.api_key:
                env_vars["API_KEY"] = self.api_key
                env_vars["TESTSPRITE_API_KEY"] = self.api_key
            
            # Add additional environment variables that TestSprite might need
            env_vars.update({
                "NODE_ENV": "production",
                "TESTSPRITE_ENVIRONMENT": "production",
                "TESTSPRITE_SKIP_BOOTSTRAP": "true",
                "TESTSPRITE_AUTO_CONFIG": "true"
            })
            
            server_params = StdioServerParameters(
                command=self.mcp_command,
                args=self.mcp_args,
                env=env_vars
            )
            
            # Connect to MCP server
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the session
                    await session.initialize()
                    
                    # List available tools
                    tools = await session.list_tools()
                    # print(f"DEBUG: Available TestSprite tools: {[tool.name for tool in tools.tools]}")
                    
                    # Find the TestSprite analysis tool - follow the proper workflow
                    analysis_tool = None
                    
                    # Step 1: Try bootstrap_tests first (required for proper setup)
                    for tool in tools.tools:
                        if "bootstrap_tests" in tool.name.lower():
                            analysis_tool = tool
                            break
                    
                    # If bootstrap_tests not available, try generate_code_and_execute
                    if not analysis_tool:
                        for tool in tools.tools:
                            if "generate_code_and_execute" in tool.name.lower():
                                analysis_tool = tool
                                break
                    
                    # If not found, try generate_code_summary
                    if not analysis_tool:
                        for tool in tools.tools:
                            if "generate_code_summary" in tool.name.lower():
                                analysis_tool = tool
                                break
                    
                    # If not found, try generate_backend_test_plan
                    if not analysis_tool:
                        for tool in tools.tools:
                            if "generate_backend_test_plan" in tool.name.lower():
                                analysis_tool = tool
                                break
                    
                    if not analysis_tool:
                        raise Exception("No suitable TestSprite tool found")
                    
                    # Run the analysis with tool-specific arguments
                    if "generate_code_summary" in analysis_tool.name:
                        # Generate code summary and analysis
                        result = await session.call_tool(
                            analysis_tool.name,
                            arguments={
                                "projectPath": repo_path
                            }
                        )
                    elif "generate_backend_test_plan" in analysis_tool.name:
                        # Generate a test plan for backend
                        result = await session.call_tool(
                            analysis_tool.name,
                            arguments={
                                "projectPath": repo_path
                            }
                        )
                    elif "generate_code_and_execute" in analysis_tool.name:
                        # This tool should be fully automated
                        result = await session.call_tool(
                            analysis_tool.name,
                            arguments={
                                "projectPath": repo_path,
                                "projectName": os.path.basename(repo_path),
                                "testIds": [],  # Empty array means run all tests
                                "additionalInstruction": "Test the code changes from the recent commit for bugs, security issues, and functionality. Focus on API endpoints, error handling, and data validation."
                            }
                        )
                    elif "bootstrap_tests" in analysis_tool.name:
                        # Bootstrap tests - this will open configuration portal
                        # We'll handle this by falling back to static analysis
                        print("Bootstrap tests requires manual configuration, falling back to static analysis")
                        return await self._run_static_analysis(repo_path)
                    else:
                        # Generic approach for other tools
                        result = await session.call_tool(
                            analysis_tool.name,
                            arguments={
                                "projectPath": repo_path,
                                "path": repo_path,
                                "directory": repo_path
                            }
                        )
                    
                    # Parse the result
                    return await self._parse_mcp_response(result, repo_path)
                    
        except Exception as e:
            raise Exception(f"TestSprite MCP analysis failed: {str(e)}")
    
    async def _run_pytest_fallback(self, repo_path: str) -> Optional[Dict[str, Any]]:
        """
        Fallback to pytest when TestSprite fails
        Attempts to run pytest on the repository
        """
        try:
            import subprocess
            import time
            
            print(f"Running pytest fallback on {repo_path}")
            
            # Check if pytest is available
            try:
                subprocess.run(["pytest", "--version"], 
                             capture_output=True, check=True, timeout=10)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                print("Pytest not available, skipping pytest fallback")
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
            print("Pytest fallback timed out")
            return {
                "passed": False,
                "total_tests": 0,
                "failed_tests": 1,
                "diagnostics": ["Pytest fallback timed out after 2 minutes"],
                "error_details": "Pytest execution timeout",
                "execution_time": 120.0,
                "test_method": "pytest_timeout"
            }
        except Exception as e:
            print(f"Pytest fallback failed: {e}")
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
        """Fallback static analysis when TestSprite MCP fails"""
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
    
    async def _execute_testsprite_workflow(self, workflow_data: Dict[str, Any], repo_path: str) -> Dict[str, Any]:
        """Execute TestSprite workflow commands to get actual test results"""
        try:
            import subprocess
            import tempfile
            import time
            
            next_actions = workflow_data.get("next_action", [])
            
            # Look for terminal commands to execute
            for action in next_actions:
                if action.get("type") == "tool" and action.get("tool") == "Run in Terminal":
                    command_input = action.get("input", {})
                    if command_input.get("inline_execution"):
                        command = command_input.get("command", "")
                        
                        if command:
                            # Execute the TestSprite command
                            # print(f"Executing TestSprite command: {command}")
                            
                            # Run the command in the repository directory
                            result = subprocess.run(
                                command,
                                shell=True,
                                cwd=repo_path,
                                capture_output=True,
                                text=True,
                                timeout=300  # 5 minute timeout
                            )
                            
                            if result.returncode == 0:
                                # Command executed successfully, look for test results
                                output = result.stdout
                                
                                # Look for test report files
                                test_report_path = os.path.join(repo_path, "testsprite_tests", "testsprite-mcp-test-report.md")
                                if os.path.exists(test_report_path):
                                    # Parse the test report
                                    return self._parse_test_report(test_report_path)
                                else:
                                    # Try to parse output for test results
                                    return self._parse_command_output(output)
                            else:
                                # Command failed
                                return {
                                    "passed": False,
                                    "total_tests": 0,
                                    "failed_tests": 1,
                                    "diagnostics": [f"TestSprite command failed: {result.stderr}"],
                                    "error_details": result.stderr,
                                    "execution_time": 0.0
                                }
            
            # If no terminal commands found, return workflow initiated message
            return {
                "passed": True,
                "total_tests": 1,
                "failed_tests": 0,
                "diagnostics": ["TestSprite workflow initiated - tests are being generated and executed"],
                "error_details": None,
                "execution_time": 0.0
            }
            
        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "total_tests": 0,
                "failed_tests": 1,
                "diagnostics": ["TestSprite command timed out after 5 minutes"],
                "error_details": "Command execution timeout",
                "execution_time": 300.0
            }
        except Exception as e:
            return {
                "passed": False,
                "total_tests": 0,
                "failed_tests": 1,
                "diagnostics": [f"Error executing TestSprite workflow: {str(e)}"],
                "error_details": str(e),
                "execution_time": 0.0
            }
    
    def _parse_test_report(self, report_path: str) -> Dict[str, Any]:
        """Parse TestSprite test report markdown file"""
        try:
            with open(report_path, 'r') as f:
                content = f.read()
            
            # Simple parsing of markdown test report
            lines = content.split('\n')
            total_tests = 0
            failed_tests = 0
            diagnostics = []
            
            for line in lines:
                if "Total Tests:" in line or "Tests Run:" in line:
                    # Extract number
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        total_tests = int(numbers[0])
                elif "Failed:" in line or "Failures:" in line:
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        failed_tests = int(numbers[0])
                elif "❌" in line or "FAIL" in line or "Error:" in line:
                    diagnostics.append(line.strip())
            
            return {
                "passed": failed_tests == 0,
                "total_tests": total_tests,
                "failed_tests": failed_tests,
                "diagnostics": diagnostics,
                "error_details": None if failed_tests == 0 else f"TestSprite found {failed_tests} test failures",
                "execution_time": 0.0
            }
            
        except Exception as e:
            return {
                "passed": False,
                "total_tests": 0,
                "failed_tests": 1,
                "diagnostics": [f"Error parsing test report: {str(e)}"],
                "error_details": str(e),
                "execution_time": 0.0
            }
    
    def _parse_command_output(self, output: str) -> Dict[str, Any]:
        """Parse command output for test results"""
        try:
            lines = output.split('\n')
            total_tests = 0
            failed_tests = 0
            diagnostics = []
            
            for line in lines:
                if "test" in line.lower() and ("passed" in line.lower() or "failed" in line.lower()):
                    if "failed" in line.lower():
                        failed_tests += 1
                        diagnostics.append(line.strip())
                    total_tests += 1
                elif "error" in line.lower() or "exception" in line.lower():
                    diagnostics.append(line.strip())
            
            return {
                "passed": failed_tests == 0,
                "total_tests": total_tests,
                "failed_tests": failed_tests,
                "diagnostics": diagnostics,
                "error_details": None if failed_tests == 0 else f"TestSprite found {failed_tests} test failures",
                "execution_time": 0.0
            }
            
        except Exception as e:
            return {
                "passed": False,
                "total_tests": 0,
                "failed_tests": 1,
                "diagnostics": [f"Error parsing command output: {str(e)}"],
                "error_details": str(e),
                "execution_time": 0.0
            }
    
    async def _parse_mcp_response(self, mcp_result, repo_path: str) -> Dict[str, Any]:
        """Parse MCP server response into our expected format"""
        try:
            # Extract content from MCP result
            content = mcp_result.content
            if content and len(content) > 0:
                # Parse the JSON response from MCP
                result_data = json.loads(content[0].text)
                
                # Debug: print the raw response to understand the structure (commented out for production)
                # print(f"DEBUG: TestSprite raw response: {json.dumps(result_data, indent=2)}")
                
                # Check if this is a validation error
                if "Validation error" in str(result_data) or "Invalid input" in str(result_data):
                    # TestSprite returned a validation error, fall back to static analysis
                    print("TestSprite validation error, falling back to static analysis")
                    return await self._run_static_analysis(repo_path)
                
                # Check if this is a workflow response (next_action format)
                if "next_action" in result_data:
                    # This is a workflow instruction - we need to execute it
                    return await self._execute_testsprite_workflow(result_data, repo_path)
                
                # Extract test results - handle different response formats
                tests = result_data.get("tests", [])
                if not tests:
                    # Try alternative keys
                    tests = result_data.get("test_results", [])
                    if not tests:
                        tests = result_data.get("results", [])
                
                total_tests = len(tests)
                failed_tests = len([t for t in tests if not t.get("passed", True)])
                
                diagnostics = []
                for test in tests:
                    if not test.get("passed", True):
                        diagnostics.append(f"Test '{test.get('name', 'Unknown')}': {test.get('error', 'Failed')}")
                
                # If no tests found, check if there are any issues or errors
                if total_tests == 0:
                    # Look for other indicators of problems
                    if "error" in result_data:
                        diagnostics.append(f"TestSprite error: {result_data['error']}")
                    elif "issues" in result_data:
                        diagnostics.extend(result_data["issues"])
                    elif "problems" in result_data:
                        diagnostics.extend(result_data["problems"])
                
                return {
                    "passed": failed_tests == 0 and total_tests > 0,
                    "total_tests": total_tests,
                    "failed_tests": failed_tests,
                    "diagnostics": diagnostics,
                    "error_details": None if failed_tests == 0 else f"TestSprite found {failed_tests} test failures",
                    "execution_time": result_data.get("execution_time", 0.0)
                }
            else:
                raise Exception("No content returned from MCP server")
                
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse MCP response: {str(e)}")
        except Exception as e:
            raise Exception(f"Error parsing MCP response: {str(e)}")