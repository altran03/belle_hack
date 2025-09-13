import os
import json
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from datetime import datetime

class GeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.mock_mode = os.getenv("GEMINI_MOCK", "0") == "1"
        
        if not self.mock_mode and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    async def analyze_code_and_generate_patch(self, 
                                            repo_path: str,
                                            commit_sha: str,
                                            commit_message: str,
                                            testsprite_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze code issues and generate a patch using Gemini
        """
        if self.mock_mode:
            return await self._mock_analysis(repo_path, commit_message, testsprite_result)
        
        try:
            # Build context for Gemini
            context = self._build_analysis_context(repo_path, commit_sha, commit_message, testsprite_result)
            
            # Generate prompt
            prompt = self._build_analysis_prompt(context)
            
            # Get response from Gemini
            response = self.model.generate_content(prompt)
            
            # Parse response
            return self._parse_gemini_response(response.text)
            
        except Exception as e:
            return {
                "issue_summary": f"Error in Gemini analysis: {str(e)}",
                "bugs_detected": [str(e)],
                "optimizations": [],
                "patch": "",
                "deployable_status": "unknown",
                "confidence_score": 0.0
            }
    
    def _build_analysis_context(self, repo_path: str, commit_sha: str, 
                              commit_message: str, testsprite_result: Dict[str, Any]) -> Dict[str, Any]:
        """Build context for Gemini analysis"""
        from pathlib import Path
        
        # Get key files from the repository
        python_files = list(Path(repo_path).rglob("*.py"))
        
        # Read key files (limit to avoid token limits)
        file_contents = {}
        for py_file in python_files[:5]:  # Limit to 5 files
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
            "commit_sha": commit_sha,
            "commit_message": commit_message,
            "testsprite_result": testsprite_result,
            "file_contents": file_contents,
            "repo_structure": [str(f.relative_to(repo_path)) for f in python_files]
        }
    
    def _build_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Build the prompt for Gemini analysis"""
        prompt = f"""
You are BugSniper Pro, an AI debugging agent. Analyze the following code and test results to identify bugs, issues, and optimizations.

COMMIT INFORMATION:
- SHA: {context['commit_sha']}
- Message: {context['commit_message']}

TESTSPRITE RESULTS:
- Passed: {context['testsprite_result']['passed']}
- Total Tests: {context['testsprite_result']['total_tests']}
- Failed Tests: {context['testsprite_result']['failed_tests']}
- Diagnostics: {json.dumps(context['testsprite_result']['diagnostics'], indent=2)}

CODE FILES:
"""
        
        for file_path, content in context['file_contents'].items():
            prompt += f"\n--- {file_path} ---\n{content}\n"
        
        prompt += """

ANALYSIS REQUIREMENTS:
1. Identify specific bugs and issues in the code
2. Suggest optimizations and improvements
3. Generate a unified diff patch that fixes the issues
4. Determine if the code is deployable after fixes
5. Provide a confidence score (0.0 to 1.0)

RESPONSE FORMAT (JSON):
{
    "issue_summary": "Brief summary of issues found",
    "bugs_detected": ["list", "of", "specific", "bugs"],
    "optimizations": ["list", "of", "optimizations"],
    "patch": "unified diff patch content",
    "deployable_status": "deployable|not_deployable|unknown",
    "confidence_score": 0.85
}

Focus on:
- Syntax errors and logical bugs
- Security vulnerabilities
- Performance issues
- Code quality improvements
- Missing error handling
- Unused imports/variables

Generate a clean, minimal patch that fixes the most critical issues.
"""
        
        return prompt
    
    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini response and extract structured data"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # Fallback parsing
                return self._fallback_parse(response_text)
        except Exception as e:
            return self._fallback_parse(response_text)
    
    def _fallback_parse(self, response_text: str) -> Dict[str, Any]:
        """Fallback parsing when JSON parsing fails"""
        return {
            "issue_summary": "Analysis completed with issues detected",
            "bugs_detected": ["Code analysis completed"],
            "optimizations": ["Review code for improvements"],
            "patch": "",
            "deployable_status": "unknown",
            "confidence_score": 0.5
        }
    
    async def _mock_analysis(self, repo_path: str, commit_message: str, 
                           testsprite_result: Dict[str, Any]) -> Dict[str, Any]:
        """Mock Gemini analysis for development/testing"""
        import asyncio
        await asyncio.sleep(2)  # Simulate processing time
        
        # Generate mock analysis based on test results
        bugs_detected = []
        optimizations = []
        
        if not testsprite_result['passed']:
            bugs_detected.extend([
                "Potential syntax error detected",
                "Missing error handling",
                "Unused imports found"
            ])
        
        optimizations.extend([
            "Add type hints for better code clarity",
            "Implement proper logging",
            "Add input validation"
        ])
        
        # Generate a simple mock patch
        patch = """--- a/sample.py
+++ b/sample.py
@@ -1,5 +1,7 @@
 def hello_world():
-    print("Hello, World!")
+    \"\"\"Print a greeting message.\"\"\"
+    print("Hello, World!")
+    return "Hello, World!"
 
 def main():
-    hello_world()
+    \"\"\"Main function.\"\"\"
+    return hello_world()
"""
        
        deployable_status = "deployable" if testsprite_result['failed_tests'] == 0 else "not_deployable"
        confidence_score = 0.8 if testsprite_result['failed_tests'] < 3 else 0.6
        
        return {
            "issue_summary": f"Found {len(bugs_detected)} issues in commit '{commit_message}'",
            "bugs_detected": bugs_detected,
            "optimizations": optimizations,
            "patch": patch,
            "deployable_status": deployable_status,
            "confidence_score": confidence_score
        }
