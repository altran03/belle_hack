# BugSniper Pro Sample Repository

This is a sample Python repository with deliberate bugs and issues for testing BugSniper Pro.

## Issues Included

This repository contains various types of issues that BugSniper Pro should detect and fix:

### Security Issues
- Use of `eval()` function
- Use of `exec()` function
- Potential code injection vulnerabilities

### Code Quality Issues
- Bare except clauses
- Missing docstrings
- Unused imports
- Unused variables
- Inconsistent naming conventions

### Performance Issues
- Inefficient algorithms
- Memory inefficient operations
- Resource leaks (unclosed files)

### Error Handling Issues
- Missing exception handling
- Division by zero potential
- No input validation

### Python 2 Compatibility Issues
- Print statements without parentheses

## How to Use

1. Push this repository to GitHub
2. Connect it to BugSniper Pro
3. Make a commit to trigger the webhook
4. Watch BugSniper Pro detect and fix the issues

## Files

- `main.py` - Main application with various bugs
- `requirements.txt` - Python dependencies
- `README.md` - This file

## Expected Fixes

BugSniper Pro should:
1. Add proper exception handling
2. Remove unused imports and variables
3. Add docstrings to functions and classes
4. Replace `eval()` and `exec()` with safer alternatives
5. Add type hints
6. Fix resource leaks
7. Optimize inefficient algorithms
8. Add input validation
9. Fix Python 2 compatibility issues
