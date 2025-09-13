import os
import subprocess
import json
import tempfile
from typing import Dict, Any, List, Optional
import asyncio
from pathlib import Path

class TestSpriteClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TESTSPRITE_API_KEY")
        self.mock_mode = os.getenv("TESTSPRITE_MOCK", "0") == "1"
    
    async def run_tests(self, repo_path: str) -> Dict[str, Any]:
        """
        Run TestSprite tests on the repository
        Returns test results with diagnostics
        """
        if self.mock_mode:
            return await self._mock_test_results(repo_path)
        
        try:
            # For now, we'll use a mock implementation
            # In a real implementation, you would use the TestSprite SDK
            return await self._mock_test_results(repo_path)
            
        except Exception as e:
            return {
                "passed": False,
                "total_tests": 0,
                "failed_tests": 1,
                "diagnostics": [f"TestSprite error: {str(e)}"],
                "error_details": str(e),
                "execution_time": 0.0
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