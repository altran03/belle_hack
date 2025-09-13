from typing import Dict, Any, List
import json

class PromptBuilder:
    def __init__(self):
        pass
    
    def build_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Build a comprehensive prompt for Gemini analysis"""
        prompt = f"""
You are BugSniper Pro, an advanced AI debugging agent. Analyze the following code and test results to identify bugs, security issues, and optimization opportunities.

COMMIT CONTEXT:
- SHA: {context.get('commit_sha', 'unknown')}
- Message: {context.get('commit_message', 'No message')}
- Author: {context.get('commit_author', 'unknown')}

TESTSPRITE ANALYSIS:
- Tests Passed: {context.get('testsprite_result', {}).get('passed', False)}
- Total Tests: {context.get('testsprite_result', {}).get('total_tests', 0)}
- Failed Tests: {context.get('testsprite_result', {}).get('failed_tests', 0)}
- Diagnostics: {json.dumps(context.get('testsprite_result', {}).get('diagnostics', []), indent=2)}

CODE FILES TO ANALYZE:
"""
        
        # Add file contents
        file_contents = context.get('file_contents', {})
        for file_path, content in file_contents.items():
            prompt += f"\n--- {file_path} ---\n{content}\n"
        
        prompt += """

ANALYSIS REQUIREMENTS:
1. **Bug Detection**: Identify specific bugs, syntax errors, and logical issues
2. **Security Analysis**: Find security vulnerabilities and unsafe practices
3. **Performance Issues**: Detect performance bottlenecks and inefficiencies
4. **Code Quality**: Identify code quality issues and best practice violations
5. **Optimization Opportunities**: Suggest improvements and optimizations

RESPONSE FORMAT (JSON only):
{
    "issue_summary": "Concise summary of all issues found",
    "bugs_detected": ["specific", "list", "of", "bugs"],
    "optimizations": ["list", "of", "optimizations"],
    "patch": "unified diff patch content",
    "deployable_status": "deployable|not_deployable|unknown",
    "confidence_score": 0.85
}

FOCUS AREAS:
- Syntax errors and runtime exceptions
- Security vulnerabilities (SQL injection, XSS, etc.)
- Performance issues (inefficient algorithms, memory leaks)
- Code quality (unused variables, missing docstrings, etc.)
- Error handling and edge cases
- Type safety and input validation

Generate a minimal, focused patch that addresses the most critical issues.
Ensure the patch is syntactically correct and follows best practices.
"""
        
        return prompt
    
    def build_summary_prompt(self, analysis_results: Dict[str, Any]) -> str:
        """Build a prompt for generating user-friendly summaries"""
        prompt = f"""
Generate a user-friendly summary of the BugSniper Pro analysis:

ANALYSIS RESULTS:
- Issues Found: {len(analysis_results.get('bugs_detected', []))}
- Optimizations: {len(analysis_results.get('optimizations', []))}
- Deployable Status: {analysis_results.get('deployable_status', 'unknown')}
- Confidence: {analysis_results.get('confidence_score', 0.0):.2f}

Create a clear, concise summary that explains:
1. What issues were found
2. What fixes were applied
3. Whether the code is ready for deployment
4. Any recommendations for the developer

Keep it under 200 words and use plain language.
"""
        
        return prompt