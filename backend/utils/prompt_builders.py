from typing import Dict, Any, List
import json

class PromptBuilder:
    def __init__(self):
        pass
    
    def build_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Build a comprehensive prompt for Gemini analysis"""
        prompt = f"""
You are BugSniper Pro, an advanced AI debugging agent powered by Gemini 1.5 Pro, specializing in comprehensive code analysis. Analyze the following code and test results to identify bugs, security issues, and optimization opportunities with maximum specificity and detail. Use your advanced reasoning capabilities to provide deep, accurate analysis.

COMMIT CONTEXT:
- SHA: {context.get('commit_sha', 'unknown')}
- Message: {context.get('commit_message', 'No message')}
- Author: {context.get('commit_author', 'unknown')}
- Repository Structure: {json.dumps(context.get('repo_structure', []), indent=2)}

TESTSPRITE ANALYSIS:
- Tests Passed: {context.get('testsprite_result', {}).get('passed', False)}
- Total Tests: {context.get('testsprite_result', {}).get('total_tests', 0)}
- Failed Tests: {context.get('testsprite_result', {}).get('failed_tests', 0)}
- Execution Time: {context.get('testsprite_result', {}).get('execution_time', 'unknown')}
- Detailed Diagnostics: {json.dumps(context.get('testsprite_result', {}).get('diagnostics', []), indent=2)}

CODE FILES TO ANALYZE:
"""
        
        # Add file contents with line numbers for better reference
        file_contents = context.get('file_contents', {})
        for file_path, content in file_contents.items():
            # Add line numbers to help with specific references
            lines = content.split('\n')
            numbered_content = '\n'.join(f"{i+1:4d}| {line}" for i, line in enumerate(lines))
            prompt += f"\n--- {file_path} ---\n{numbered_content}\n"
        
        prompt += """

DETAILED ANALYSIS REQUIREMENTS:
1. **Bug Detection**: Identify specific bugs with exact line numbers, file names, and detailed explanations
2. **Security Analysis**: Find security vulnerabilities with specific attack vectors and remediation steps
3. **Performance Issues**: Detect performance bottlenecks with specific metrics and optimization suggestions
4. **Code Quality**: Identify code quality issues with specific examples and improvement recommendations
5. **Error Handling**: Analyze error handling patterns and suggest specific improvements
6. **Type Safety**: Check for type-related issues and suggest specific type annotations
7. **Dependencies**: Analyze import statements and suggest specific dependency optimizations

ENHANCED RESPONSE FORMAT (JSON only - NO markdown code blocks):
IMPORTANT: Return ONLY valid JSON, no markdown formatting, no code blocks, no explanations.

{
    "issue_summary": "Brief summary of issues found",
    "bugs_detected": [
        {
            "type": "syntax_error|logical_bug|runtime_error|security_vulnerability|exception_handling|code_quality|performance",
            "severity": "critical|high|medium|low",
            "file": "specific_file_path",
            "line": line_number,
            "description": "Concise one-line description of the issue",
            "impact": "Brief impact statement",
            "reproduction": "Simple reproduction steps"
        }
    ],
    "optimizations": [
        {
            "type": "performance|security|maintainability|readability",
            "file": "specific_file_path",
            "line": line_number,
            "current_approach": "Brief current approach",
            "suggested_approach": "Brief improvement suggestion",
            "benefit": "Expected benefit"
        }
    ],
    "patch": "unified diff patch content with specific line references",
    "deployable_status": "deployable|not_deployable|unknown",
    "confidence_score": 0.85,
    "analysis_details": {
        "files_analyzed": ["list", "of", "files"],
        "total_issues_found": number,
        "critical_issues": number,
        "security_issues": number,
        "performance_issues": number,
        "code_quality_issues": number
    }
}

SPECIFIC FOCUS AREAS WITH EXAMPLES:
- **Syntax Errors**: Missing colons, incorrect indentation, undefined variables
- **Logical Bugs**: Off-by-one errors, incorrect conditionals, wrong variable usage
- **Security Vulnerabilities**: SQL injection, XSS, path traversal, insecure deserialization
- **Performance Issues**: N+1 queries, inefficient loops, memory leaks, unoptimized algorithms
- **Code Quality**: Unused imports, missing docstrings, inconsistent naming, code duplication
- **Error Handling**: Missing try-catch blocks, unhandled exceptions, poor error messages
- **Type Safety**: Missing type hints, incorrect type usage, type mismatches
- **Best Practices**: PEP 8 violations, anti-patterns, deprecated functions

ANALYSIS INSTRUCTIONS:
1. Examine each file line by line for potential issues
2. Cross-reference imports with actual usage
3. Check for common Python pitfalls and anti-patterns
4. Analyze test results to understand failure patterns
5. Consider the commit message for context about intended changes
6. Provide specific line numbers and file references for all issues
7. Suggest concrete, actionable improvements
8. Prioritize issues by severity and impact

BUG DESCRIPTION GUIDELINES:
- Keep descriptions concise (1 sentence max)
- Focus on the core issue only
- Use clear, direct language
- Include specific problem and location
- Examples: "Missing colon (line 80)", "Division by zero risk (line 18)", "Unsafe eval() usage (line 36)"

OPTIMIZATION DESCRIPTION GUIDELINES:
- Keep suggestions brief and actionable
- Focus on the key improvement only
- Examples: "Use Counter() for O(n) performance", "Replace eval() with ast.literal_eval()", "Use context manager"

DEPLOYMENT READINESS CRITERIA:
Determine deployable_status based on the following comprehensive criteria:

**DEPLOYABLE** - Code is safe to deploy when:
- No critical or high-severity bugs found
- No security vulnerabilities present
- All tests pass OR test failures are minor (low-severity issues only)
- No syntax errors or runtime errors that would prevent execution
- No breaking changes to public APIs
- Error handling is adequate for production use

**NOT DEPLOYABLE** - Code should NOT be deployed when:
- Any critical bugs present (syntax errors, runtime errors, security vulnerabilities)
- Any high-severity bugs that could cause data loss, crashes, or security issues
- Test failures indicate functional problems
- Missing error handling for critical operations
- Performance issues that could cause timeouts or resource exhaustion
- Breaking changes without proper migration paths

**UNKNOWN** - Deployment status unclear when:
- Insufficient test coverage to determine stability
- Mixed severity issues requiring manual review
- Complex dependencies or external integrations not fully tested
- Analysis confidence is below 70%

CONFIDENCE SCORE GUIDELINES:
- 0.9-1.0: High confidence, comprehensive analysis completed
- 0.7-0.89: Good confidence, most issues identified
- 0.5-0.69: Moderate confidence, some analysis limitations
- 0.0-0.49: Low confidence, significant analysis gaps

Generate a comprehensive analysis with concise, readable descriptions and actionable recommendations.
Ensure the patch addresses the most critical issues with precise line-level changes.
Make deployment decisions based on the severity and impact of all identified issues.
"""
        
        return prompt
    
    def build_summary_prompt(self, analysis_results: Dict[str, Any]) -> str:
        """Build a prompt for generating user-friendly summaries"""
        bugs_detected = analysis_results.get('bugs_detected', [])
        optimizations = analysis_results.get('optimizations', [])
        analysis_details = analysis_results.get('analysis_details', {})
        
        # Count issues by type and severity
        critical_issues = sum(1 for bug in bugs_detected if isinstance(bug, dict) and bug.get('severity') == 'critical')
        high_issues = sum(1 for bug in bugs_detected if isinstance(bug, dict) and bug.get('severity') == 'high')
        security_issues = sum(1 for bug in bugs_detected if isinstance(bug, dict) and bug.get('type') == 'security_vulnerability')
        
        prompt = f"""
Generate a comprehensive, user-friendly summary of the BugSniper Pro analysis:

ANALYSIS RESULTS:
- Total Issues Found: {len(bugs_detected)}
- Critical Issues: {critical_issues}
- High Priority Issues: {high_issues}
- Security Issues: {security_issues}
- Optimizations Suggested: {len(optimizations)}
- Deployable Status: {analysis_results.get('deployable_status', 'unknown')}
- Confidence Score: {analysis_results.get('confidence_score', 0.0):.2f}
- Files Analyzed: {len(analysis_details.get('files_analyzed', []))}

DETAILED BREAKDOWN:
{json.dumps(analysis_results, indent=2)}

Create a clear, detailed summary that explains:
1. **Issue Overview**: Specific types and counts of issues found
2. **Critical Findings**: Most important issues that need immediate attention
3. **Security Concerns**: Any security vulnerabilities and their impact
4. **Performance Issues**: Bottlenecks and optimization opportunities
5. **Code Quality**: Areas for improvement in maintainability and readability
6. **Fixes Applied**: Specific changes made in the patch
7. **Deployment Readiness**: Whether the code is safe to deploy
8. **Developer Recommendations**: Next steps and best practices

Format the summary with:
- Clear headings and bullet points
- Specific file names and line numbers where relevant
- Actionable recommendations
- Risk assessment for each issue type

Keep it comprehensive but accessible, under 400 words, using clear technical language.
"""
        
        return prompt