import os
import json
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from datetime import datetime
from utils.prompt_builders import PromptBuilder

class GeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.mock_mode = os.getenv("GEMINI_MOCK", "0") == "1"
        self.prompt_builder = PromptBuilder()
        
        if not self.mock_mode and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-pro')  # Upgraded to Pro for better analysis
            # Configure generation parameters for better responses
            self.generation_config = {
                "temperature": 0.1,  # Lower temperature for more consistent JSON
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 4096  # Reduced token limit to prevent truncation
            }
    
    async def generate_tests(self, repo_path: str) -> Dict[str, Any]:
        """
        Generate test files for the repository using Gemini
        """
        if self.mock_mode:
            return await self._mock_test_generation(repo_path)
        
        try:
            # Build context for test generation
            context = self._build_test_generation_context(repo_path)
            
            # Generate prompt for test creation
            prompt = self._build_test_generation_prompt(context)
            
            # Get response from Gemini
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            # Parse and save generated tests
            return self._parse_and_save_tests(response.text, repo_path)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to generate tests: {str(e)}",
                "test_files": []
            }

    async def analyze_code_and_generate_patch(self, 
                                            repo_path: str,
                                            commit_sha: str,
                                            commit_message: str,
                                            testsprite_result: Dict[str, Any],
                                            commit_author: str = "unknown") -> Dict[str, Any]:
        """
        Analyze code issues and generate a patch using Gemini
        """
        if self.mock_mode:
            return await self._mock_analysis(repo_path, commit_message, testsprite_result)
        
        try:
            # Build context for Gemini
            context = self._build_analysis_context(repo_path, commit_sha, commit_message, testsprite_result, commit_author)
            
            # Generate prompt using the improved PromptBuilder
            prompt = self.prompt_builder.build_analysis_prompt(context)
            
            # Get response from Gemini with improved configuration
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            # Parse response
            result = self._parse_gemini_response(response.text)
            # Normalize the response format
            return self._normalize_response_format(result)
            
        except Exception as e:
            return {
                "issue_summary": f"Error in Gemini analysis: {str(e)}",
                "bugs_detected": [
                    {
                        "type": "runtime_error",
                        "severity": "critical",
                        "file": "gemini_client.py",
                        "line": 0,
                        "description": f"Gemini API error: {str(e)}",
                        "impact": "Analysis could not be completed",
                        "reproduction": "Check Gemini API configuration and network connectivity"
                    }
                ],
                "optimizations": [],
                "patch": "",
                "deployable_status": "not_deployable",  # Critical error means not deployable
                "confidence_score": 0.0
            }
    
    def _build_analysis_context(self, repo_path: str, commit_sha: str, 
                              commit_message: str, testsprite_result: Dict[str, Any], 
                              commit_author: str = "unknown") -> Dict[str, Any]:
        """Build comprehensive context for Gemini analysis"""
        from pathlib import Path
        
        # Get key files from the repository
        python_files = list(Path(repo_path).rglob("*.py"))
        
        # Prioritize important files (main.py, models, utils, etc.)
        priority_files = []
        other_files = []
        
        for py_file in python_files:
            file_path = str(py_file.relative_to(repo_path))
            if any(keyword in file_path.lower() for keyword in ['main.py', 'models', 'utils', 'api', 'routes', 'handlers']):
                priority_files.append(py_file)
            else:
                other_files.append(py_file)
        
        # Combine priority files first, then others
        ordered_files = priority_files + other_files
        
        # Read key files (limit to avoid token limits but prioritize important files)
        file_contents = {}
        for py_file in ordered_files[:8]:  # Increased limit to 8 files
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Truncate if too long but preserve more content
                    if len(content) > 3000:
                        content = content[:3000] + "\n... (truncated)"
                    file_contents[str(py_file.relative_to(repo_path))] = content
            except Exception as e:
                file_contents[str(py_file.relative_to(repo_path))] = f"Error reading file: {e}"
        
        # Get additional context about the repository
        repo_info = {
            "total_python_files": len(python_files),
            "file_sizes": {str(f.relative_to(repo_path)): f.stat().st_size for f in python_files[:10]},
            "has_requirements": (Path(repo_path) / "requirements.txt").exists(),
            "has_tests": any("test" in str(f).lower() for f in python_files),
            "has_config": any("config" in str(f).lower() for f in python_files)
        }
        
        return {
            "commit_sha": commit_sha,
            "commit_message": commit_message,
            "commit_author": commit_author,
            "testsprite_result": testsprite_result,
            "file_contents": file_contents,
            "repo_structure": [str(f.relative_to(repo_path)) for f in python_files],
            "repo_info": repo_info
        }
    
    
    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini response and extract structured data"""
        try:
            import re
            
            # Log the response for debugging
            print(f"Gemini response length: {len(response_text)} characters")
            print(f"First 200 chars: {response_text[:200]}")
            print(f"Last 200 chars: {response_text[-200:]}")
            
            # First try to extract JSON from markdown code blocks
            json_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_block_match:
                json_str = json_block_match.group(1)
                print(f"Found JSON in code block, length: {len(json_str)}")
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"JSON block parsing failed: {e}")
                    # Try to fix the JSON
                    fixed_json = self._fix_truncated_json(json_str)
                    return json.loads(fixed_json)
            
            # Try to parse as direct JSON (no markdown)
            try:
                return json.loads(response_text.strip())
            except json.JSONDecodeError as e:
                print(f"Direct JSON parsing failed: {e}")
            
            # If no code blocks, try to find JSON object directly
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                print(f"Found JSON object, length: {len(json_str)}")
                # Try to fix common truncation issues
                json_str = self._fix_truncated_json(json_str)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"Fixed JSON parsing failed: {e}")
            
            # If still no JSON found, try to parse the entire response as JSON
            try:
                fixed_response = self._fix_truncated_json(response_text.strip())
                return json.loads(fixed_response)
            except json.JSONDecodeError as e:
                print(f"Full response JSON parsing failed: {e}")
            
            # Fallback parsing
            print("Using fallback parsing")
            return self._fallback_parse(response_text)
        except Exception as e:
            print(f"Error parsing Gemini response: {e}")
            print(f"Response text: {response_text[:500]}...")
            return self._fallback_parse(response_text)
    
    def _fix_truncated_json(self, json_str: str) -> str:
        """Attempt to fix common JSON truncation issues"""
        try:
            # If it's already valid JSON, return as is
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Error position: line {e.lineno}, column {e.colno}")
            
            # Try to fix common truncation patterns
            fixed_json = json_str
            
            # If it ends with incomplete string, try to close it
            if fixed_json.count('"') % 2 == 1:  # Odd number of quotes
                # Find the last unclosed quote and close the string
                last_quote_pos = fixed_json.rfind('"')
                if last_quote_pos > 0:
                    # Check if this quote is inside a string value
                    before_quote = fixed_json[:last_quote_pos]
                    if before_quote.count('"') % 2 == 0:  # This is an opening quote
                        fixed_json = fixed_json[:last_quote_pos + 1] + '"'
            
            # If it ends with incomplete array or object, try to close them
            open_braces = fixed_json.count('{') - fixed_json.count('}')
            open_brackets = fixed_json.count('[') - fixed_json.count(']')
            
            # Close incomplete objects and arrays
            if open_braces > 0:
                fixed_json += '}' * open_braces
            if open_brackets > 0:
                fixed_json += ']' * open_brackets
            
            # If it ends with a comma, remove it
            fixed_json = fixed_json.rstrip().rstrip(',')
            
            # Try to parse the fixed JSON
            try:
                json.loads(fixed_json)
                print("Successfully fixed truncated JSON")
                return fixed_json
            except json.JSONDecodeError as e2:
                print(f"Fixed JSON still invalid: {e2}")
                # If still invalid, try to extract partial data
                return self._extract_partial_json(json_str)
    
    def _extract_partial_json(self, json_str: str) -> str:
        """Extract partial JSON data when full parsing fails"""
        import re
        
        print("Attempting to extract partial JSON data...")
        
        # Try to extract what we can from the response
        issue_summary = "Analysis completed with partial results"
        bugs_detected = []
        optimizations = []
        
        # Look for issue summary
        summary_match = re.search(r'"issue_summary":\s*"([^"]*)"', json_str)
        if summary_match:
            issue_summary = summary_match.group(1)
            print(f"Found issue summary: {issue_summary}")
        
        # Look for bugs detected - try multiple patterns
        bugs_match = re.search(r'"bugs_detected":\s*\[(.*?)\]', json_str, re.DOTALL)
        if bugs_match:
            bugs_content = bugs_match.group(1)
            print(f"Found bugs content, length: {len(bugs_content)}")
            
            # Try to extract individual bug objects with more flexible patterns
            # Pattern 1: Full bug objects
            bug_matches = re.findall(r'\{[^}]*"type":\s*"([^"]*)"[^}]*"severity":\s*"([^"]*)"[^}]*"file":\s*"([^"]*)"[^}]*"line":\s*(\d+)[^}]*"description":\s*"([^"]*)"', bugs_content)
            for bug_match in bug_matches:
                bugs_detected.append({
                    "type": bug_match[0],
                    "severity": bug_match[1],
                    "file": bug_match[2],
                    "line": int(bug_match[3]),
                    "description": bug_match[4],
                    "impact": "Issue identified in code analysis",
                    "reproduction": "Review the specific line and file mentioned"
                })
            
            # Pattern 2: If no full matches, try to extract partial bug info
            if not bug_matches:
                # Look for individual bug entries
                bug_entries = re.findall(r'\{[^}]*\}', bugs_content)
                print(f"Found {len(bug_entries)} bug entries")
                for entry in bug_entries:
                    type_match = re.search(r'"type":\s*"([^"]*)"', entry)
                    severity_match = re.search(r'"severity":\s*"([^"]*)"', entry)
                    file_match = re.search(r'"file":\s*"([^"]*)"', entry)
                    line_match = re.search(r'"line":\s*(\d+)', entry)
                    desc_match = re.search(r'"description":\s*"([^"]*)"', entry)
                    
                    if type_match and severity_match and file_match and line_match and desc_match:
                        bugs_detected.append({
                            "type": type_match.group(1),
                            "severity": severity_match.group(1),
                            "file": file_match.group(1),
                            "line": int(line_match.group(1)),
                            "description": desc_match.group(1),
                            "impact": "Issue identified in code analysis",
                            "reproduction": "Review the specific line and file mentioned"
                        })
        
        # Also look for critical issues mentioned in the issue summary
        if "syntax error" in issue_summary.lower() or "prevents execution" in issue_summary.lower():
            bugs_detected.append({
                "type": "syntax_error",
                "severity": "critical",
                "file": "unknown",
                "line": 0,
                "description": "Syntax error preventing code execution",
                "impact": "Code cannot run",
                "reproduction": "Run the code to see syntax error"
            })
        
        if "security" in issue_summary.lower() or "vulnerability" in issue_summary.lower():
            bugs_detected.append({
                "type": "security_vulnerability",
                "severity": "critical",
                "file": "unknown",
                "line": 0,
                "description": "Security vulnerability detected",
                "impact": "Security risk",
                "reproduction": "Check security analysis"
            })
        
        # If no bugs found, add a generic one
        if not bugs_detected:
            bugs_detected.append({
                "type": "code_quality",
                "severity": "medium",
                "file": "unknown",
                "line": 0,
                "description": "Analysis response was truncated",
                "impact": "Incomplete analysis results",
                "reproduction": "Check Gemini API response limits"
            })
        
        # Determine deployment status based on extracted bugs
        deployable_status = "unknown"
        if bugs_detected:
            # Check if any critical or high severity bugs were found
            critical_issues = sum(1 for bug in bugs_detected if bug.get('severity') == 'critical')
            high_issues = sum(1 for bug in bugs_detected if bug.get('severity') == 'high')
            security_issues = sum(1 for bug in bugs_detected if bug.get('type') == 'security_vulnerability')
            syntax_errors = sum(1 for bug in bugs_detected if bug.get('type') == 'syntax_error')
            
            if critical_issues > 0 or security_issues > 0 or syntax_errors > 0:
                deployable_status = "not_deployable"
            elif high_issues > 0:
                deployable_status = "not_deployable"
            else:
                deployable_status = "unknown"
        
        # Create a minimal valid JSON response
        return json.dumps({
            "issue_summary": issue_summary,
            "bugs_detected": bugs_detected,
            "optimizations": optimizations,
            "patch": "",
            "deployable_status": deployable_status,
            "confidence_score": 0.3
        })
    
    def _build_test_generation_context(self, repo_path: str) -> Dict[str, Any]:
        """Build context for test generation"""
        from pathlib import Path
        
        # Get Python files from the repository
        python_files = list(Path(repo_path).rglob("*.py"))
        
        # Read key files for test generation
        file_contents = {}
        for py_file in python_files[:5]:  # Limit to 5 files to avoid token limits
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Truncate if too long
                    if len(content) > 2000:
                        content = content[:2000] + "\n... (truncated)"
                    file_contents[str(py_file.relative_to(repo_path))] = content
            except Exception as e:
                file_contents[str(py_file.relative_to(repo_path))] = f"Error reading file: {e}"
        
        return {
            "file_contents": file_contents,
            "repo_structure": [str(f.relative_to(repo_path)) for f in python_files],
            "total_files": len(python_files)
        }
    
    def _build_test_generation_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for test generation"""
        prompt = f"""
You are an expert Python test generator. Generate comprehensive test files for the following Python code.

REPOSITORY STRUCTURE:
{context.get('repo_structure', [])}

CODE FILES TO TEST:
"""
        
        # Add file contents with line numbers
        file_contents = context.get('file_contents', {})
        for file_path, content in file_contents.items():
            lines = content.split('\n')
            numbered_content = '\n'.join(f"{i+1:4d}| {line}" for i, line in enumerate(lines))
            prompt += f"\n--- {file_path} ---\n{numbered_content}\n"
        
        prompt += """

TEST GENERATION REQUIREMENTS:
1. **Comprehensive Coverage**: Create tests for all functions, classes, and methods
2. **Edge Cases**: Include tests for edge cases, error conditions, and boundary values
3. **Mocking**: Use unittest.mock for external dependencies
4. **Fixtures**: Use pytest fixtures where appropriate
5. **Assertions**: Include meaningful assertions that verify expected behavior
6. **Documentation**: Add docstrings to test functions explaining what they test

RESPONSE FORMAT (JSON only):
{
    "test_files": [
        {
            "file_path": "test_filename.py",
            "content": "complete test file content with imports, classes, and test methods"
        }
    ],
    "test_summary": "Brief summary of what tests were generated",
    "coverage_areas": ["list of areas covered by tests"]
}

TEST FILE NAMING CONVENTIONS:
- For main.py: test_main.py
- For utils/helpers.py: test_helpers.py
- For models/user.py: test_user.py
- For api/handlers.py: test_handlers.py

Generate comprehensive, well-structured test files that will help identify bugs and ensure code quality.
"""
        
        return prompt
    
    def _parse_and_save_tests(self, response_text: str, repo_path: str) -> Dict[str, Any]:
        """Parse Gemini response and save test files"""
        try:
            import re
            import os
            
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                return {
                    "success": False,
                    "error": "No JSON found in response",
                    "test_files": []
                }
            
            json_str = json_match.group()
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError:
                # Try to fix common JSON issues
                json_str = self._fix_truncated_json(json_str)
                result = json.loads(json_str)
            
            # Save test files
            test_files = []
            for test_file in result.get("test_files", []):
                file_path = test_file.get("file_path")
                content = test_file.get("content")
                
                if file_path and content:
                    # Create test directory if it doesn't exist
                    test_dir = os.path.join(repo_path, "tests")
                    os.makedirs(test_dir, exist_ok=True)
                    
                    # Save test file
                    full_path = os.path.join(test_dir, file_path)
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    test_files.append(full_path)
            
            return {
                "success": True,
                "test_files": test_files,
                "test_summary": result.get("test_summary", "Tests generated successfully"),
                "coverage_areas": result.get("coverage_areas", [])
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to parse and save tests: {str(e)}",
                "test_files": []
            }
    
    async def _mock_test_generation(self, repo_path: str) -> Dict[str, Any]:
        """Mock test generation for development/testing"""
        import asyncio
        import os
        
        await asyncio.sleep(1)  # Simulate processing time
        
        # Create a simple mock test file
        test_dir = os.path.join(repo_path, "tests")
        os.makedirs(test_dir, exist_ok=True)
        
        test_content = '''import unittest
from unittest.mock import patch, MagicMock

class TestMain(unittest.TestCase):
    """Test cases for main functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        pass
    
    def test_basic_functionality(self):
        """Test basic functionality works."""
        # Mock test - replace with actual tests based on your code
        self.assertTrue(True)
    
    def test_error_handling(self):
        """Test error handling."""
        with self.assertRaises(ValueError):
            raise ValueError("Test error")
    
    @patch('builtins.print')
    def test_print_functionality(self, mock_print):
        """Test print functionality with mock."""
        print("test message")
        mock_print.assert_called_once_with("test message")

if __name__ == '__main__':
    unittest.main()
'''
        
        test_file_path = os.path.join(test_dir, "test_main.py")
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        return {
            "success": True,
            "test_files": [test_file_path],
            "test_summary": "Mock test file generated for development",
            "coverage_areas": ["basic functionality", "error handling", "print functionality"]
        }
    
    def _normalize_response_format(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize the response format to ensure consistency"""
        # Ensure bugs_detected is a list of objects
        if "bugs_detected" in result:
            bugs = result["bugs_detected"]
            if isinstance(bugs, list):
                normalized_bugs = []
                for bug in bugs:
                    if isinstance(bug, str):
                        # Convert string to object format
                        normalized_bugs.append({
                            "type": "code_quality",
                            "severity": "medium",
                            "file": "unknown",
                            "line": 0,
                            "description": bug,
                            "impact": "Issue identified",
                            "reproduction": "Check code"
                        })
                    elif isinstance(bug, dict):
                        # Ensure all required fields are present and normalize values
                        severity = bug.get("severity", "medium")
                        if isinstance(severity, str):
                            severity = severity.lower()
                            if severity in ["critical", "high", "medium", "low"]:
                                pass  # Already normalized
                            elif severity in ["severe", "major"]:
                                severity = "high"
                            elif severity in ["minor", "info"]:
                                severity = "low"
                            else:
                                severity = "medium"
                        
                        normalized_bug = {
                            "type": bug.get("type", "code_quality"),
                            "severity": severity,
                            "file": bug.get("file", "unknown"),
                            "line": bug.get("line", 0),
                            "description": bug.get("description", "Issue identified"),
                            "impact": bug.get("impact", "Issue identified"),
                            "reproduction": bug.get("reproduction", "Check code")
                        }
                        normalized_bugs.append(normalized_bug)
                result["bugs_detected"] = normalized_bugs
        
        # Ensure optimizations is a list of objects
        if "optimizations" in result:
            optimizations = result["optimizations"]
            if isinstance(optimizations, list):
                normalized_optimizations = []
                for opt in optimizations:
                    if isinstance(opt, str):
                        # Convert string to object format
                        normalized_optimizations.append({
                            "type": "maintainability",
                            "file": "unknown",
                            "line": 0,
                            "current_approach": "Current implementation",
                            "suggested_approach": opt,
                            "benefit": "Improved code quality"
                        })
                    elif isinstance(opt, dict):
                        # Ensure all required fields are present
                        normalized_opt = {
                            "type": opt.get("type", "maintainability"),
                            "file": opt.get("file", "unknown"),
                            "line": opt.get("line", 0),
                            "current_approach": opt.get("current_approach", "Current implementation"),
                            "suggested_approach": opt.get("suggested_approach", "Improvement suggested"),
                            "benefit": opt.get("benefit", "Improved code quality")
                        }
                        normalized_optimizations.append(normalized_opt)
                result["optimizations"] = normalized_optimizations
        
        # Ensure deployable_status is a string
        if "deployable_status" in result:
            status = result["deployable_status"]
            if isinstance(status, bool):
                result["deployable_status"] = "deployable" if status else "not_deployable"
            elif isinstance(status, str):
                # Normalize string values
                status_lower = status.lower()
                if status_lower in ["true", "deployable", "yes", "ready to deploy", "ready for deployment"]:
                    result["deployable_status"] = "deployable"
                elif status_lower in ["false", "not_deployable", "no", "not ready", "not ready to deploy"]:
                    result["deployable_status"] = "not_deployable"
                else:
                    result["deployable_status"] = "unknown"
        
        # Ensure confidence_score is a float
        if "confidence_score" in result:
            score = result["confidence_score"]
            if isinstance(score, str):
                try:
                    result["confidence_score"] = float(score)
                except:
                    result["confidence_score"] = 0.5
            elif not isinstance(score, (int, float)):
                result["confidence_score"] = 0.5
        
        return result
    
    def _fallback_parse(self, response_text: str) -> Dict[str, Any]:
        """Fallback parsing when JSON parsing fails"""
        return {
            "issue_summary": "Analysis completed with parsing issues detected",
            "bugs_detected": [
                {
                    "type": "code_quality",
                    "severity": "high",
                    "file": "gemini_client.py",
                    "line": 0,
                    "description": "Unable to parse detailed analysis from Gemini response",
                    "impact": "Analysis results may be incomplete or inaccurate",
                    "reproduction": "Check Gemini API response format and parsing logic"
                }
            ],
            "optimizations": [
                {
                    "type": "maintainability",
                    "file": "gemini_client.py",
                    "line": 0,
                    "current_approach": "Fallback parsing used due to response format issues",
                    "suggested_approach": "Improve Gemini response parsing and prompt formatting",
                    "benefit": "More reliable and accurate analysis results"
                }
            ],
            "patch": "",
            "deployable_status": "not_deployable",  # Parsing failure indicates analysis issues
            "confidence_score": 0.2  # Very low confidence due to parsing failure
        }
    
    async def _mock_analysis(self, repo_path: str, commit_message: str, 
                           testsprite_result: Dict[str, Any]) -> Dict[str, Any]:
        """Mock Gemini analysis for development/testing with enhanced format"""
        import asyncio
        await asyncio.sleep(2)  # Simulate processing time
        
        # Generate mock analysis based on test results with enhanced format
        bugs_detected = []
        optimizations = []
        
        if not testsprite_result['passed']:
            bugs_detected.extend([
                {
                    "type": "syntax_error",
                    "severity": "high",
                    "file": "main.py",
                    "line": 15,
                    "description": "Missing colon after if statement",
                    "impact": "Code will not execute due to syntax error",
                    "reproduction": "Run the code and observe SyntaxError"
                },
                {
                    "type": "logical_bug",
                    "severity": "medium",
                    "file": "utils/helpers.py",
                    "line": 42,
                    "description": "Variable used before assignment in error handling",
                    "impact": "Potential NameError at runtime",
                    "reproduction": "Trigger error condition to see NameError"
                }
            ])
        else:
            bugs_detected.extend([
                {
                    "type": "code_quality",
                    "severity": "low",
                    "file": "models/schemas.py",
                    "line": 8,
                    "description": "Unused import statement",
                    "impact": "Code bloat and potential confusion",
                    "reproduction": "Check imports in the file"
                }
            ])
        
        optimizations.extend([
            {
                "type": "maintainability",
                "file": "main.py",
                "line": 1,
                "current_approach": "No type hints for function parameters",
                "suggested_approach": "Add type hints using typing module",
                "benefit": "Better IDE support and code documentation"
            },
            {
                "type": "performance",
                "file": "api/handlers.py",
                "line": 25,
                "current_approach": "Using list comprehension in loop",
                "suggested_approach": "Use generator expression or optimize algorithm",
                "benefit": "Reduced memory usage and faster execution"
            }
        ])
        
        # Generate a more realistic mock patch
        patch = """--- a/main.py
+++ b/main.py
@@ -12,7 +12,7 @@ def process_data(data: List[str]) -> Dict[str, Any]:
     try:
         result = {}
         for item in data:
-            if item is not None
+            if item is not None:
                 result[item] = len(item)
         return result
     except Exception as e:
@@ -20,6 +20,7 @@ def process_data(data: List[str]) -> Dict[str, Any]:
         return {"error": str(e)}
 
 def main():
+    \"\"\"Main entry point for the application.\"\"\"
     data = ["hello", "world", None, "test"]
     result = process_data(data)
     print(result)
"""
        
        # Enhanced deployment logic based on bug severity and types
        critical_issues = sum(1 for bug in bugs_detected if bug.get('severity') == 'critical')
        high_issues = sum(1 for bug in bugs_detected if bug.get('severity') == 'high')
        security_issues = sum(1 for bug in bugs_detected if bug.get('type') == 'security_vulnerability')
        syntax_errors = sum(1 for bug in bugs_detected if bug.get('type') == 'syntax_error')
        runtime_errors = sum(1 for bug in bugs_detected if bug.get('type') == 'runtime_error')
        
        # Determine deployment status based on comprehensive criteria
        if critical_issues > 0 or security_issues > 0 or syntax_errors > 0 or runtime_errors > 0:
            deployable_status = "not_deployable"
        elif high_issues > 0 and testsprite_result['failed_tests'] > 0:
            deployable_status = "not_deployable"
        elif high_issues > 0 and testsprite_result['failed_tests'] == 0:
            deployable_status = "unknown"  # High severity issues but tests pass - needs review
        elif testsprite_result['failed_tests'] == 0:
            deployable_status = "deployable"
        else:
            deployable_status = "unknown"  # Test failures but no critical issues - needs review
        
        # Calculate confidence score based on analysis completeness
        total_issues = len(bugs_detected)
        if total_issues == 0 and testsprite_result['passed']:
            confidence_score = 0.95  # High confidence when no issues found
        elif critical_issues > 0 or security_issues > 0:
            confidence_score = 0.9   # High confidence for critical issues
        elif total_issues <= 3:
            confidence_score = 0.85  # Good confidence for few issues
        elif total_issues <= 6:
            confidence_score = 0.75  # Moderate confidence for several issues
        else:
            confidence_score = 0.65  # Lower confidence for many issues
        
        return {
            "issue_summary": f"Analysis completed for commit '{commit_message}': Found {len(bugs_detected)} issues across multiple categories",
            "bugs_detected": bugs_detected,
            "optimizations": optimizations,
            "patch": patch,
            "deployable_status": deployable_status,
            "confidence_score": confidence_score,
            "analysis_details": {
                "files_analyzed": ["main.py", "utils/helpers.py", "models/schemas.py", "api/handlers.py"],
                "total_issues_found": len(bugs_detected),
                "critical_issues": sum(1 for bug in bugs_detected if bug.get('severity') == 'critical'),
                "security_issues": sum(1 for bug in bugs_detected if bug.get('type') == 'security_vulnerability'),
                "performance_issues": sum(1 for opt in optimizations if opt.get('type') == 'performance'),
                "code_quality_issues": sum(1 for bug in bugs_detected if bug.get('type') == 'code_quality')
            }
        }
